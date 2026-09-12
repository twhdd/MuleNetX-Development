import { useEffect, useState } from "react";

export default function SystemOverview() {

    const [data,setData] =
        useState(null);

    useEffect(() => {

        fetch(
            "http://localhost:8000/api/dashboard/summary"
        )
        .then(r=>r.json())
        .then(setData);

    }, []);

    if(!data)
        return null;

    return (

        <div>

            <h2>
                MuleNetX
            </h2>

            <p>
                Accounts:
                {data.total_accounts}
            </p>

            <p>
                Avg Risk:
                {
                    Number(
                        data.avg_risk
                    ).toFixed(4)
                }
            </p>

            <p>
                Max Risk:
                {
                    Number(
                        data.max_risk
                    ).toFixed(4)
                }
            </p>

        </div>
    );
}
