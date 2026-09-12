import {
    useEffect,
    useState
} from "react";

export default function AlertCenter() {

    const [alerts,setAlerts] =
        useState([]);

    async function load() {

        const response =
        await fetch(
            "http://localhost:8000/api/stream/events"
        );

        const data =
        await response.json();

        setAlerts(data);
    }

    useEffect(() => {

        load();

        const interval =
        setInterval(
            load,
            2000
        );

        return () =>
            clearInterval(
                interval
            );

    }, []);

    return (

        <div>

            <h2>
                Alert Center
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

                        [{alert.risk}]

                        {" "}

                        {alert.source}

                        →

                        {alert.target}

                        {" "}

                        {alert.amount}

                        <hr/>

                    </div>

                ))
            }

        </div>
    );
}
