import {
    useEffect,
    useState
} from "react";

export default function LiveTransactionFeed() {

    const [rows,setRows] =
        useState([]);

    async function load() {

        const response =
        await fetch(
            "http://localhost:8000/api/transactions/live"
        );

        const data =
        await response.json();

        setRows(data);
    }

    useEffect(() => {

        load();

        const interval =
        setInterval(
            load,
            3000
        );

        return () =>
            clearInterval(
                interval
            );

    }, []);

    return (

        <div>

            <h2>
                Live Transactions
            </h2>

            {
                rows.map(
                    (
                        tx,
                        index
                    ) => (

                    <div
                        key={index}
                    >

                        {tx.tx}

                        <br/>

                        Amount:
                        {tx.amount}

                        <hr/>

                    </div>

                ))
            }

        </div>
    );
}
