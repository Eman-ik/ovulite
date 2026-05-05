import { useEffect, useState } from "react";

export function LoginDebugPage() {
  const [result, setResult] = useState("Loading...");
  const [credentials, setCredentials] = useState({
    username: "lab_tech",
    password: "ovulite2026",
  });

  const testLogin = async () => {
    setResult("Testing...");
    try {
      const params = new URLSearchParams();
      params.append("username", credentials.username);
      params.append("password", credentials.password);

      console.log("🔍 Making login request:", {
        url: "http://localhost:8000/auth/login",
        method: "POST",
        body: `username=${credentials.username}&password=${credentials.password}`,
      });

      const response = await fetch("http://localhost:8000/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      });

      console.log("📊 Response:", {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers),
      });

      const data = await response.json();
      console.log("📦 Response body:", data);

      if (response.ok) {
        setResult(
          `✓ SUCCESS!\n\n` +
            `Access Token: ${data.access_token?.slice(0, 50)}...\n` +
            `Refresh Token: ${data.refresh_token?.slice(0, 50)}...`
        );
      } else {
        setResult(
          `✗ FAILED (${response.status})\n\n` +
            `${JSON.stringify(data, null, 2)}`
        );
      }
    } catch (error) {
      console.error("❌ Network error:", error);
      setResult(`❌ Network Error:\n${(error as Error).message}`);
    }
  };

  useEffect(() => {
    testLogin();
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 p-8 text-white font-mono">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">🔐 Login Debug Page</h1>

        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Test Credentials</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-sm mb-1">Username:</label>
              <input
                type="text"
                value={credentials.username}
                onChange={(e) =>
                  setCredentials({ ...credentials, username: e.target.value })
                }
                className="w-full bg-slate-700 p-2 rounded text-white"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Password:</label>
              <input
                type="password"
                value={credentials.password}
                onChange={(e) =>
                  setCredentials({ ...credentials, password: e.target.value })
                }
                className="w-full bg-slate-700 p-2 rounded text-white"
              />
            </div>
          </div>
          <button
            onClick={testLogin}
            className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-bold"
          >
            Test Login
          </button>
        </div>

        <div className="bg-slate-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">Result:</h2>
          <pre className="bg-slate-900 p-4 rounded text-yellow-300 whitespace-pre-wrap text-sm overflow-auto max-h-96">
            {result}
          </pre>
        </div>

        <div className="mt-6 text-xs text-slate-400">
          <p>✓ Check browser console (F12) for detailed logs</p>
          <p>✓ Backend must be running on http://localhost:8000</p>
          <p>✓ Test usernames: admin, lab_tech, et_tech</p>
          <p>✓ All passwords: ovulite2026</p>
        </div>
      </div>
    </div>
  );
}

export default LoginDebugPage;
