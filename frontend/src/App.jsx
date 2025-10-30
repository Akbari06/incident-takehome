import { useEffect, useMemo, useState } from "react";

const palette = ["#c7d2fe", "#bbf7d0", "#fcd34d", "#fbcfe8", "#bae6fd", "#fed7aa"];

const defaultSchedule = {
  users: ["alice", "bob", "charlie"],
  handover_start_at: "2025-11-07T17:00:00Z",
  handover_interval_days: 7,
};

const defaultOverrides = [
  {
    user: "charlie",
    start_at: "2025-11-10T17:00:00Z",
    end_at: "2025-11-10T22:00:00Z",
  },
];

const defaultWindow = {
  from: "2025-11-07T17:00:00Z",
  until: "2025-11-21T17:00:00Z",
};

function App() {
  const [scheduleText, setScheduleText] = useState(JSON.stringify(defaultSchedule, null, 2));
  const [overridesText, setOverridesText] = useState(JSON.stringify(defaultOverrides, null, 2));
  const [window, setWindow] = useState(defaultWindow);
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const timeFormatter = useMemo(() => {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  }, []);

  const userColour = useMemo(() => {
    const map = new Map();
    let idx = 0;
    return (user) => {
      if (!map.has(user)) {
        map.set(user, palette[idx % palette.length]);
        idx += 1;
      }
      return map.get(user);
    };
  }, []);

  const fetchSchedule = async () => {
    setError("");
    let schedule;
    let overrides;
    try {
      schedule = JSON.parse(scheduleText);
    } catch (parseError) {
      setError(`Schedule JSON invalid: ${parseError.message}`);
      return;
    }

    try {
      overrides = JSON.parse(overridesText);
    } catch (parseError) {
      setError(`Overrides JSON invalid: ${parseError.message}`);
      return;
    }

    if (!window.from || !window.until) {
      setError("Both window fields are required.");
      return;
    }

    setLoading(true);
    try {
      const formatTimestamp = (value) => timeFormatter.format(new Date(value));

      const response = await fetch("http://localhost:8000/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schedule,
          overrides,
          from: window.from,
          until: window.until,
        }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Request failed");
      }

      const data = await response.json();
      setEntries(
        data.map((entry) => ({
          ...entry,
          formattedStart: formatTimestamp(entry.start_at),
          formattedEnd: formatTimestamp(entry.end_at),
        })),
      );
    } catch (requestError) {
      setError(requestError.message);
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule().catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalRange = useMemo(() => {
    const start = Date.parse(window.from);
    const end = Date.parse(window.until);
    if (Number.isNaN(start) || Number.isNaN(end) || end <= start) {
      return null;
    }
    return {
      start,
      end,
      length: end - start,
      labelStart: timeFormatter.format(new Date(window.from)),
      labelEnd: timeFormatter.format(new Date(window.until)),
    };
  }, [timeFormatter, window.from, window.until]);

  return (
    <div className="layout">
      <header className="header">
        <h1>Incident Schedule Visualiser</h1>
        <p>
          Update the schedule JSON and click render to see how overrides affect the final rotation.
        </p>
      </header>

      <section className="panels vertical">
        <form
          className="panel"
          onSubmit={(event) => {
            event.preventDefault();
            fetchSchedule();
          }}
        >
          <h2>Configuration</h2>
          <label className="field">
            <span>Schedule JSON</span>
            <textarea
              value={scheduleText}
              onChange={(event) => setScheduleText(event.target.value)}
              rows={8}
            />
          </label>
          <label className="field">
            <span>Overrides JSON</span>
            <textarea
              value={overridesText}
              onChange={(event) => setOverridesText(event.target.value)}
              rows={6}
            />
          </label>
          <div className="range-fields">
            <label className="field">
              <span>From</span>
              <input
                type="text"
                name="from"
                value={window.from}
                onChange={(event) => setWindow({ ...window, from: event.target.value })}
                placeholder="2025-11-07T17:00:00Z"
              />
            </label>
            <label className="field">
              <span>Until</span>
              <input
                type="text"
                name="until"
                value={window.until}
                onChange={(event) => setWindow({ ...window, until: event.target.value })}
                placeholder="2025-11-21T17:00:00Z"
              />
            </label>
          </div>
          <button type="submit" className="primary">
            {loading ? "Rendering…" : "Render schedule"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>

        <section className="panel panel-wide">
          <h2>Timeline</h2>
          {totalRange && entries.length > 0 ? (
            <div className="timeline timeline-expanded">
              <div className="timeline-track">
                <div className="timeline-track-inner">
                  {entries.map((entry) => {
                    const start = Date.parse(entry.start_at);
                    const end = Date.parse(entry.end_at);
                    const duration = Math.max(end - start, 0);
                    const flexShare = duration / totalRange.length || 0;
                    return (
                      <div
                        key={`${entry.user}-${entry.start_at}`}
                        className="timeline-segment"
                        style={{
                          flexGrow: Math.max(flexShare, 0.0001),
                          backgroundColor: userColour(entry.user),
                        }}
                        title={`${entry.user}: ${entry.start_at} → ${entry.end_at}`}
                      >
                        <div className="segment-content">
                          <div className="segment-user">{entry.user}</div>
                          <div className="segment-range">
                            {entry.formattedStart} → {entry.formattedEnd}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="timeline-scale">
                <span>{totalRange.labelStart}</span>
                <span>{totalRange.labelEnd}</span>
              </div>
            </div>
          ) : (
            <p className="empty">Run the renderer to visualise the schedule.</p>
          )}
        </section>

        <section className="panel">
          <h2>Entries</h2>
          {entries.length > 0 ? (
            <table className="entries">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Start</th>
                  <th>End</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={`${entry.user}-${entry.start_at}-table`}>
                    <td>{entry.user}</td>
                    <td>{entry.start_at}</td>
                    <td>{entry.end_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty">No entries available.</p>
          )}
        </section>
      </section>
    </div>
  );
}

export default App;
