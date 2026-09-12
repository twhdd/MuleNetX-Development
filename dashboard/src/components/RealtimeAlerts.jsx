import {
    useEffect,
    useState
} from "react";

export default function RealtimeAlerts() {

    const [events,setEvents] =
        useState([]);

    useEffect(() => {

        const socket =
        new WebSocket(
            "ws://localhost:8000/ws/live"
        );

        socket.onmessage =
        (event) => {

            const data =
            JSON.parse(
                event.data
            );

            setEvents(
                prev => [
                    data,
                    ...prev
                ]
            );
        };

        return () =>
            socket.close();

    }, []);

    return (

        <div>

            <h2>
                Live Alerts
            </h2>

            {
                events.map(
                    (
                        e,
                        i
                    ) => (

                    <div
                        key={i}
                    >

                        {e.risk}

                        {" | "}

                        {e.amount}

                    </div>

                ))
            }

        </div>

    );
}
