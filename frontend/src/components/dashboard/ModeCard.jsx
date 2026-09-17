import { Link } from "react-router-dom";

function ModeCard({
    icon,
    title,
    description,
    theme,
    to,
}) {
    return (
        <div
            className={`
    glass-card
    gaming-card
    rounded-3xl
    p-6
    min-h-[220px]
    ${theme}
  `}
        >

            <div className="text-5xl mb-5">
                {icon}
            </div>

            <h3 className="text-2xl font-bold text-white">
                {title}
            </h3>

            <p className="text-gray-400 mt-2">
                {description}
            </p>

            <Link to={to} className="mt-6 inline-block text-cyan-400">
                Start Now →
            </Link>

        </div>
    );
}

export default ModeCard;