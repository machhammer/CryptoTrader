import React, { useState, useEffect } from "react";

function News() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/news")
      .then((response) => response.json())
      .then((json) => setData(json))
      .catch((error) => console.error(error));
  }, []);

  if (Array.isArray(data)) {
    console.log(data.length);
  }

  return (
    <div>
      News
      <table>
        <thead>
          <tr>
            <th>First name</th>
            <th>Last name</th>
          </tr>
        </thead>
        <tbody>{data[(0, 1)]}</tbody>
      </table>
    </div>
  );
}

export default News;
