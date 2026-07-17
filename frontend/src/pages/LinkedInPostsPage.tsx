import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Share2, Plus, ExternalLink, User, Loader2 } from 'lucide-react';
import api from '../lib/api';
import { FilterBar, SelectFilter } from '../components/FilterBar';
import { ScoreBadge } from '../components/ScoreBadge';

interface Post {
  id: string;
  post_url: string | null;
  poster_name: string | null;
  raw_text: string;
  match_score: number | null;
  match_rationale: string | null;
  country: string | null;
  sponsorship: string;
  source: string;
  submitted_at: string;
  scored_at: string | null;
}

const sponsorshipOptions = [
  { value: 'yes', label: '✅ Sponsors' },
  { value: 'no', label: '❌ No Sponsorship' },
  { value: 'unknown', label: '❓ Unknown' },
];

export function LinkedInPostsPage() {
  const [search, setSearch] = useState('');
  const [country, setCountry] = useState('');
  const [sponsorship, setSponsorship] = useState('');
  const [page, setPage] = useState(1);
  const [showManual, setShowManual] = useState(false);
  const [manualUrl, setManualUrl] = useState('');
  const [manualText, setManualText] = useState('');
  const [manualPoster, setManualPoster] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['linkedin-posts', { search, country, sponsorship, page }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (country) params.country = country;
      if (sponsorship) params.sponsorship = sponsorship;
      if (search) params.min_score = 0;
      const res = await api.get('/linkedin-posts', { params });
      return res.data as { items: Post[]; total: number; page: number; page_size: number };
    },
    refetchInterval: 30000,
  });

  const addMutation = useMutation({
    mutationFn: async () => {
      await api.post('/linkedin-posts/manual', {
        post_url: manualUrl || undefined,
        raw_text: manualText,
        poster_name: manualPoster || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['linkedin-posts'] });
      setShowManual(false);
      setManualUrl('');
      setManualText('');
      setManualPoster('');
    },
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-(--color-text-primary) flex items-center gap-2">
            <Share2 className="w-6 h-6 text-(--color-accent)" />
            LinkedIn Posts
          </h1>
          <p className="text-sm text-(--color-text-secondary) mt-1">
            {data?.total ?? 0} scored posts · Auto-refreshes every 30s
          </p>
        </div>
        <button
          onClick={() => setShowManual(!showManual)}
          className="flex items-center gap-1.5 px-4 py-2 text-sm bg-(--color-accent) hover:bg-(--color-accent-hover) text-white rounded-(--radius-md) transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Manually
        </button>
      </div>

      {/* Manual Add Form */}
      {showManual && (
        <div className="bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-5 shadow-(--shadow-card) space-y-3">
          <h3 className="text-sm font-medium text-(--color-text-primary)">Add a LinkedIn Post Manually</h3>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="url"
              value={manualUrl}
              onChange={(e) => setManualUrl(e.target.value)}
              placeholder="Post URL (optional)"
              className="px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none"
            />
            <input
              type="text"
              value={manualPoster}
              onChange={(e) => setManualPoster(e.target.value)}
              placeholder="Poster name (optional)"
              className="px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none"
            />
          </div>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            placeholder="Paste the post text here..."
            rows={4}
            className="w-full px-3 py-2 bg-(--color-bg-input) border border-(--color-border-default) rounded-(--radius-md) text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:border-(--color-border-focus) focus:outline-none resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => addMutation.mutate()}
              disabled={!manualText.trim() || addMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-(--color-accent) hover:bg-(--color-accent-hover) text-white rounded-(--radius-md) transition-colors disabled:opacity-50"
            >
              {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add Post'}
            </button>
            <button
              onClick={() => setShowManual(false)}
              className="px-4 py-2 text-sm text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      <FilterBar
        searchValue={search}
        onSearchChange={(v) => { setSearch(v); setPage(1); }}
        searchPlaceholder="Search posts..."
      >
        <SelectFilter
          value={country}
          onChange={(v) => { setCountry(v); setPage(1); }}
          options={[
            { value: 'US', label: '🇺🇸 United States' },
            { value: 'UK', label: '🇬🇧 United Kingdom' },
            { value: 'CA', label: '🇨🇦 Canada' },
            { value: 'DE', label: '🇩🇪 Germany' },
            { value: 'IN', label: '🇮🇳 India' },
          ]}
          placeholder="All Countries"
        />
        <SelectFilter
          value={sponsorship}
          onChange={(v) => { setSponsorship(v); setPage(1); }}
          options={sponsorshipOptions}
          placeholder="All Sponsorship"
        />
      </FilterBar>

      {/* Error */}
      {error && (
        <div className="p-4 bg-(--color-error-subtle) text-(--color-error) rounded-(--radius-md) text-sm">
          Failed to load posts. Please try again.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-(--color-bg-card) rounded-(--radius-lg) animate-pulse border border-(--color-border-default)" />
          ))}
        </div>
      )}

      {/* Posts */}
      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((post) => (
            <div
              key={post.id}
              className="group bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-4 hover:border-(--color-accent)/30 hover:shadow-(--shadow-glow) transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    {post.poster_name && (
                      <span className="flex items-center gap-1 text-sm font-medium text-(--color-text-primary)">
                        <User className="w-3.5 h-3.5 text-(--color-accent)" />
                        {post.poster_name}
                      </span>
                    )}
                    {post.post_url && (
                      <a
                        href={post.post_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-(--color-accent)" />
                      </a>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      post.source === 'extension' ? 'bg-(--color-info-subtle) text-(--color-info)' : 'bg-(--color-bg-elevated) text-(--color-text-muted)'
                    }`}>
                      {post.source === 'extension' ? '🔌 Extension' : '✍️ Manual'}
                    </span>
                  </div>
                  <p className="text-sm text-(--color-text-secondary) line-clamp-3">
                    {post.raw_text}
                  </p>
                  {post.match_rationale && (
                    <p className="text-xs text-(--color-text-muted) mt-2 italic">
                      {post.match_rationale}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-(--color-text-muted)">
                    {post.country && <span>📍 {post.country}</span>}
                    <span className={
                      post.sponsorship === 'yes' ? 'text-(--color-success)' :
                      post.sponsorship === 'no' ? 'text-(--color-error)' : ''
                    }>
                      {post.sponsorship === 'yes' ? '✅ Sponsors' :
                       post.sponsorship === 'no' ? '❌ No Visa' : '❓ Unknown'}
                    </span>
                    <span>{new Date(post.submitted_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <ScoreBadge score={post.match_score} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {data && data.items.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <Share2 className="w-12 h-12 text-(--color-text-muted) mx-auto mb-3" />
          <h3 className="text-lg font-medium text-(--color-text-primary)">No LinkedIn posts yet</h3>
          <p className="text-sm text-(--color-text-secondary) mt-1 max-w-md mx-auto">
            Install the Chrome extension to automatically detect hiring posts, or add them manually above.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-md) text-(--color-text-secondary) hover:bg-(--color-bg-hover) disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-(--color-text-muted) tabular-nums">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-md) text-(--color-text-secondary) hover:bg-(--color-bg-hover) disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
