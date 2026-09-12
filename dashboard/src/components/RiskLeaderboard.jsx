import { useEffect, useState } from "react";

export default function RiskLeaderboard() {

    const [rows, setRows] = useState([]);

    useEffect(() => {

        fetch(
            "http://localhost:8000/api/risk/top"
        )
        .then(r => r.json())
        .then(setRows);

    }, []);

    return (
        <div>

            <h2>
                Top Risk Accounts
            </h2>

            <table>

                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Risk</th>
                    </tr>
                </thead>

                <tbody>

                {
                    rows.map((row,index) => (

                        <tr key={index}>
                            <td>{row.account}</td>
                            <td>
                                {Number(
                                    row.risk
                                ).toFixed(4)}
                            </td>
                        </tr>

                    ))
                }

                </tbody>

            </table>

        </div>
    );
}
