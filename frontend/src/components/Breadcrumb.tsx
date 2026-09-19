import { Link, useNavigate } from "react-router-dom";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  const navigate = useNavigate();
  const parent = items.length >= 2 ? items[items.length - 2] : null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4" data-testid="breadcrumb">
      {parent?.to && (
        <button
          onClick={() => navigate(parent.to!)}
          className="sm:hidden flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-2 transition-colors"
          aria-label={parent.label}
          data-testid="breadcrumb-back"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          {parent.label}
        </button>
      )}
      <ol className="hidden sm:flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-1">
            {i > 0 && (
              <svg
                className="h-3 w-3 text-gray-400 dark:text-slate-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            )}
            {item.to ? (
              <Link
                to={item.to}
                className="hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-gray-900 dark:text-white font-medium">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
