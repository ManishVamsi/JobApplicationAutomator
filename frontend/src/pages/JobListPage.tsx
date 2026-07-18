import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Briefcase, ExternalLink, MapPin, Building2, Globe } from 'lucide-react';
import api from '../lib/api';
import { FilterBar, SelectFilter } from '../components/FilterBar';
import { ScoreBadge } from '../components/ScoreBadge';

interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  country: string | null;
  url: string | null;
  match_score: number | null;
  match_rationale: string | null;
  sponsorship: string;
  fetched_at: string;
}

const sponsorshipOptions = [
  { value: 'yes', label: '✅ Sponsors' },
  { value: 'no', label: '❌ No Sponsorship' },
  { value: 'unknown', label: '❓ Unknown' },
];

export function JobListPage() {
  const [search, setSearch] = useState('');
  const [country, setCountry] = useState('');
  const [sponsorship, setSponsorship] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs', { search, country, sponsorship, page }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (search) params.search = search;
      if (country) params.country = country;
      if (sponsorship) params.sponsorship = sponsorship;
      const res = await api.get('/jobs', { params });
      return res.data as { items: Job[]; total: number; page: number; page_size: number };
    },
    refetchInterval: 30000,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-(--color-text-primary) flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-(--color-accent)" />
          Job Listings
        </h1>
        <p className="text-sm text-(--color-text-muted) mt-0.5">
          {data?.total ?? 0} jobs found · Auto-refreshes every 30s
        </p>
      </div>

      {/* Filters */}
      <FilterBar
        searchValue={search}
        onSearchChange={(v) => { setSearch(v); setPage(1); }}
        searchPlaceholder="Search by title..."
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
        <div className="p-4 bg-(--color-error-bg) text-(--color-error) rounded-(--radius-md) text-sm border border-(--color-error)/10">
          Failed to load jobs. Please try again.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-(--color-bg-elevated) rounded-(--radius-lg) animate-pulse" />
          ))}
        </div>
      )}

      {/* Job list */}
      {data && data.items.length > 0 && (
        <div className="space-y-2.5">
          {data.items.map((job) => (
            <div
              key={job.id}
              className="group bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-lg) p-4 hover:border-(--color-accent)/20 hover:shadow-(--shadow-elevated) transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-(--color-text-primary) truncate">
                      {job.title}
                    </h3>
                    {job.url && (
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-(--color-accent)" />
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-(--color-text-secondary)">
                    {job.company && (
                      <span className="flex items-center gap-1">
                        <Building2 className="w-3 h-3" /> {job.company}
                      </span>
                    )}
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {job.location}
                      </span>
                    )}
                    {job.country && (
                      <span className="flex items-center gap-1">
                        <Globe className="w-3 h-3" /> {job.country}
                      </span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      job.sponsorship === 'yes' ? 'bg-(--color-success-bg) text-(--color-success)' :
                      job.sponsorship === 'no' ? 'bg-(--color-error-bg) text-(--color-error)' :
                      'bg-(--color-bg-elevated) text-(--color-text-muted)'
                    }`}>
                      {job.sponsorship === 'yes' ? '✅ Sponsors' :
                       job.sponsorship === 'no' ? '❌ No Visa' : '❓ Unknown'}
                    </span>
                  </div>
                  {job.match_rationale && (
                    <p className="text-xs text-(--color-text-muted) mt-2 line-clamp-2">
                      {job.match_rationale}
                    </p>
                  )}
                </div>
                <div className="flex-shrink-0">
                  <ScoreBadge score={job.match_score} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {data && data.items.length === 0 && !isLoading && (
        <div className="text-center py-20">
          <div className="w-14 h-14 rounded-2xl bg-(--color-bg-elevated) flex items-center justify-center mx-auto mb-4">
            <Briefcase className="w-7 h-7 text-(--color-text-muted)" />
          </div>
          <h3 className="text-base font-medium text-(--color-text-primary)">No jobs found</h3>
          <p className="text-sm text-(--color-text-muted) mt-1 max-w-sm mx-auto">
            Jobs will appear here after the daily fetch runs. Make sure you've set your target roles.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3.5 py-1.5 text-sm bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-md) text-(--color-text-secondary) hover:bg-(--color-bg-hover) hover:text-(--color-text-primary) disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Previous
          </button>
          <span className="text-sm text-(--color-text-muted) tabular-nums px-2">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3.5 py-1.5 text-sm bg-(--color-bg-card) border border-(--color-border-default) rounded-(--radius-md) text-(--color-text-secondary) hover:bg-(--color-bg-hover) hover:text-(--color-text-primary) disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
