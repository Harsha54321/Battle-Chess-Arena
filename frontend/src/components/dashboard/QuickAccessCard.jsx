import { Link } from "react-router-dom";

function QuickAccessCard({
    icon,
    title,
    to,
}) {
    return (
        <Link to={to} className="glass-card gaming-card rounded-2xl p-6 min-h-[120px]
flex flex-col items-center justify-center
cursor-pointer
transition-all duration-300
hover:scale-105
hover:shadow-cyanGlow">

            <div className="text-4xl mb-3">
                {icon}
            </div>

            <h3 className="text-white">
                {title}
            </h3>

        </Link>
    );
}

export default QuickAccessCard;