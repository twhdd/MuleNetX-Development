import {
    useEffect,
    useState
} from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export default function AlertFeed() {

    const [alerts,setAlerts] =
        useState([]);

    useEffect(() => {

        load();

        const interval =
        setInterval(
            load,
            10000
        );

        return () =>
            clearInterval(
                interval
            );

    }, []);

    async function load() {

        const response =
        await fetch(
            `${API_BASE_URL}/api/alerts/high-risk`
        );

        const data =
        await response.json();

        setAlerts(data);
    }

    return (

        <div>

            <h2>
                Live Alerts
            </h2>

            {
                alerts.map(
                    (
                        alert,
                        index
                    ) => (

                    <div
                        key={index}
                    >

                        {alert.account}

                        {" | "}

                        Risk:

                        {
                            Number(
                                alert.risk
                            ).toFixed(3)
                        }

                        <hr/>

                    </div>

                ))
            }

        </div>

    );
}
