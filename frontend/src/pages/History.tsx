import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dateTime, errorText, request } from "../api";
import type { Report } from "../types";
import { Empty, ErrorBox, Icon, reportStatus } from "../components/ui";

export function History() {
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(false);
  useEffect(() => {
    let active = true;
    request<Report[]>("/reports?limit=30")
      .then((data) => {
        if (active) {
          setReports(data);
          setMore(data.length === 30);
        }
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  async function loadMore() {
    setLoading(true);
    setError("");
    try {
      const data = await request<Report[]>(
        `/reports?limit=30&before=${reports[reports.length - 1].date}`,
      );
      setReports((prev) => [...prev, ...data]);
      setMore(data.length === 30);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR READING ARCHIVE</div>
          <h1>历史日报</h1>
          <p>回到某一天，重新理解当时的变化。</p>
        </div>
      </div>
      {error && <ErrorBox message={error} />}
      <div className="history-list">
        {reports.map((report) => (
          <Link
            className="history-card"
            key={report.date}
            to={`/?date=${report.date}`}
          >
            <div className="history-date">
              <strong>{report.date.slice(8)}</strong>
              <span>{report.date.slice(0, 7)}</span>
            </div>
            <div>
              <h2>{report.date} 全球新闻日报</h2>
              <p>
                {report.total} 条新闻 · {reportStatus[report.status]} · 生成于{" "}
                {dateTime(report.generated_at)}
              </p>
            </div>
            <Icon name="arrow" />
          </Link>
        ))}
      </div>
      {loading ? (
        <div className="loading" role="status">
          正在读取…
        </div>
      ) : reports.length === 0 && !error ? (
        <Empty title="还没有历史日报">
          <p>完成第一次生成后，日报会按日期自动保留。</p>
          <Link to="/" className="text-button">
            返回首页 →
          </Link>
        </Empty>
      ) : null}
      {more && !loading && (
        <button className="secondary-button" onClick={loadMore}>
          加载更早的日报
        </button>
      )}
    </>
  );
}
