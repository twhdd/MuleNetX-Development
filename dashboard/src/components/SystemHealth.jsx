import {
    useEffect,
    useState
} from "react";

export default function SystemHealth() {

    const [status,setStatus] =
        useState(null);

    useEffect(() => {

        fetch(
            "http://localhost:8000/api/dashboard/summary"
        )
        .then(r => r.json())
        .then(setStatus);

    }, []);

    if(!status)
        return null;

    return (

        <div>

            <h2>
                System Status
            </h2>

            <p>
                Accounts:
                {status.total_accounts}
            </p>

            <p>
                Avg Risk:
                {status.avg_risk}
            </p>

            <p>
                Max Risk:
                {status.max_risk}
            </p>

        </div>
    );
}
