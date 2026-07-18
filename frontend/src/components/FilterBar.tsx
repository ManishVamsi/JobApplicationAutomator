import { Search, SlidersHorizontal } from 'lucide-react';

interface FilterBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  children?: React.ReactNode;
}

export function FilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search...',
  children,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 p-3.5 bg-(--color-bg-card) rounded-(--radius-lg) border border-(--color-border-default) shadow-(--shadow-card)">
      {/* Search */}
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-(--color-text-muted)" />
        <input
          type="text"
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={searchPlaceholder}
          className="w-full pl-9 pr-3 py-2 bg-(--color-bg-elevated) border border-(--color-border-subtle) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none focus:shadow-(--shadow-glow) transition-all"
        />
      </div>

      {/* Filter controls */}
      {children && (
        <>
          <div className="h-5 w-px bg-(--color-border-default)" />
          <div className="flex items-center gap-1.5 text-(--color-text-muted)">
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </div>
          {children}
        </>
      )}
    </div>
  );
}

interface SelectFilterProps {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
}

export function SelectFilter({ value, onChange, options, placeholder }: SelectFilterProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-3 py-2 bg-(--color-bg-elevated) border border-(--color-border-subtle) rounded-(--radius-md) text-sm text-(--color-text-primary) focus:border-(--color-border-focus) focus:outline-none focus:shadow-(--shadow-glow) transition-all cursor-pointer"
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
