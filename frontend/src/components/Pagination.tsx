interface PaginationProps {
  cursor: string | null;
  onLoadMore: () => void;
  loading: boolean;
}

export function Pagination({ cursor, onLoadMore, loading }: PaginationProps) {
  if (!cursor) return null;

  return (
    <div className="flex justify-center mt-8" data-testid="pagination">
      <button
        onClick={onLoadMore}
        disabled={loading}
        className="px-6 py-2 bg-slate-700 text-white rounded-lg font-medium
          hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors"
        data-testid="load-more-button"
      >
        {loading ? "Loading..." : "Load more"}
      </button>
    </div>
  );
}
