"""One-off script: re-encrypt all Portal data keys after master key rotation.

Usage:
  python -m backend.scripts.rotate_master_key \
    --old-key-env ENCRYPTION_MASTER_KEY \
    --new-key-env ENCRYPTION_MASTER_KEY_NEW

See README.md "Operational Runbook: ENCRYPTION_MASTER_KEY Rotation" for full procedure.

Safety:
- Idempotent: safe to run multiple times (if keys haven't changed, it's a no-op).
- Transactional: batch-commits per 100 rows.
- Audited: each re-encryption logged to CredentialAccessLog.

WARNING: Running this with the wrong old key will FAIL and leave data intact.
         Running this with the right old key but wrong new key will corrupt data.
         ALWAYS test on a backup first.
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken


async def rotate_keys(old_key: str, new_key: str, batch_size: int = 100) -> None:
    """Re-encrypt all Portal.encrypted_data_key values from old_key to new_key."""
    # Validate keys before touching any data
    try:
        old_fernet = Fernet(old_key.encode())
        new_fernet = Fernet(new_key.encode())
    except Exception as e:
        print(f"ERROR: Invalid key format — {e}")
        sys.exit(1)

    # Import after validation to avoid loading the full app for bad args
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models.audit_log import CredentialAccessLog
    from app.models.portal import Portal

    rotated = 0
    errors = 0

    async with session_factory() as db:
        result = await db.execute(
            select(Portal).where(Portal.encrypted_data_key.is_not(None))
        )
        portals = list(result.scalars().all())
        total = len(portals)
        print(f"Found {total} portals with encrypted data keys")

        for i, portal in enumerate(portals):
            try:
                # Decrypt with old key
                data_key = old_fernet.decrypt(portal.encrypted_data_key)  # type: ignore[arg-type]

                # Re-encrypt with new key
                portal.encrypted_data_key = new_fernet.encrypt(data_key)

                # Audit log
                log_entry = CredentialAccessLog(
                    user_id=portal.user_id,
                    portal_id=portal.id,
                    action="master_key_rotation",
                    timestamp=datetime.now(UTC),
                )
                db.add(log_entry)
                rotated += 1

                # Batch commit
                if (i + 1) % batch_size == 0:
                    await db.commit()
                    print(f"  Committed batch {(i + 1) // batch_size} ({i + 1}/{total})")

            except InvalidToken:
                print(f"  SKIP portal {portal.id} — already re-encrypted or wrong old key")
                errors += 1
            except Exception as e:
                print(f"  ERROR portal {portal.id}: {e}")
                errors += 1

        # Final commit
        await db.commit()

    await engine.dispose()

    print(f"\nRotation complete: {rotated} re-encrypted, {errors} errors, {total} total")
    if errors > 0:
        print("WARNING: Some portals failed. Review the errors above.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate ENCRYPTION_MASTER_KEY")
    parser.add_argument(
        "--old-key-env",
        default="ENCRYPTION_MASTER_KEY",
        help="Env var name for the old master key (default: ENCRYPTION_MASTER_KEY)",
    )
    parser.add_argument(
        "--new-key-env",
        default="ENCRYPTION_MASTER_KEY_NEW",
        help="Env var name for the new master key (default: ENCRYPTION_MASTER_KEY_NEW)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Commit batch size (default: 100)",
    )
    args = parser.parse_args()

    old_key = os.environ.get(args.old_key_env)
    new_key = os.environ.get(args.new_key_env)

    if not old_key:
        print(f"ERROR: {args.old_key_env} not set in environment")
        sys.exit(1)
    if not new_key:
        print(f"ERROR: {args.new_key_env} not set in environment")
        sys.exit(1)
    if old_key == new_key:
        print("Old and new keys are identical — nothing to do.")
        sys.exit(0)

    asyncio.run(rotate_keys(old_key, new_key, args.batch_size))


if __name__ == "__main__":
    main()
