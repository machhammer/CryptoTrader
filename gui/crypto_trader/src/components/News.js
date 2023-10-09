import React, { useState, useEffect } from "react";

function News() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/news")
      .then((response) => response.json())
      .then((json) => setData(json))
      .catch((error) => console.error(error));
  }, []);

  return (
    <div>
      News
      <font size="2" face="Courier New">
        <table width="100%">
          <thead>
            <tr>
              <th align="left">Published</th>
              <th align="left">Title</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <tr key={item.id}>
                <td align="left">{item.published}</td>
                <td align="left">
                  <b>{item.title}</b>
                  <div dangerouslySetInnerHTML={{ __html: item.summary }}></div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </font>
    </div>
  );
}

export default News;
