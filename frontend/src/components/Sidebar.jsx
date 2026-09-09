import { HOST_NAME, PAGE_ORDER, PAGE_META } from "../data/pages.js";

export default function Sidebar({ currentPage, onNavigate, tourActive }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="mark">A</div>
        <div className="name">{HOST_NAME}</div>
      </div>
      <nav className="navlist">
        {PAGE_ORDER.map((id) => {
          const active = id === currentPage;
          const highlighted = tourActive && active;
          return (
            <div
              key={id}
              className={
                "navitem" +
                (active ? " active" : "") +
                (highlighted ? " tour-highlight" : "")
              }
              onClick={() => onNavigate(id)}
            >
              <span className="dot" />
              {PAGE_META[id].title}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
