import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export default function RiskLeaderboard() {

    const [rows, setRows] = useState([]);

    useEffect(() => {

        fetch(`${API_BASE_URL}/api/risk/top`)
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
                        <th>Explanation</th>
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
                            <td>{row.explanation || "No explanation available"}</td>
                        </tr>

                    ))
                }

                </tbody>

            </table>

        </div>
    );
}
