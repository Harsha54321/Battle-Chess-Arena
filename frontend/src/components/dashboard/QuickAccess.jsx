import QuickAccessCard from "./QuickAccessCard";
import {
    Users,
    Bell,
    ShoppingCart,
    Gift
} from "lucide-react";

function QuickAccess() {

    const actions = [
        {
            title: "Friends",
            icon: <Users size={32} />,
        },
        {
            title: "Notifications",
            icon: <Bell size={32} />,
        },
        {
            title: "Shop",
            icon: <ShoppingCart size={32} />,
        },
        {
            title: "Daily Rewards",
            icon: <Gift size={32} />,
        },
    ];

    return (
        <div className="mt-10">

            <h2 className="text-2xl text-white mb-6">
                QUICK ACCESS
            </h2>

            <div className="grid grid-cols-2 gap-5 md:grid-cols-4">

                {actions.map((action) => (

                    <QuickAccessCard
                        key={action.title}
                        icon={action.icon}
                        title={action.title}
                    />

                ))}

            </div>

        </div>
    );
}

export default QuickAccess;