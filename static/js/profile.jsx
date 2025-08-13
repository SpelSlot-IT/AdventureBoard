import React, { useEffect, useState } from "react";

// Simple Profile editor component
// - Fetches the current user from `meEndpoint` (default: /api/me)
// - Shows editable fields (name, email, profile picture url)
// - Sends a PATCH to `/api/users/:id` with only changed fields
// - Assumes session cookie auth (fetch uses credentials: 'include') —
//   if you use token auth, pass an `authHeader` prop or change the fetch calls.

export default function ProfileEditor({
  meEndpoint = "/api/me",
  usersEndpointBase = "/api/users",
  authHeader = null, // e.g. { Authorization: `Bearer ${token}` }
}) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [user, setUser] = useState(null); // original server response
  const [form, setForm] = useState({ name: "", email: "", profile_pic: "" });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    fetch(meEndpoint, {
      method: "GET",
      credentials: "include", // keep cookies for session-auth flows
      headers: authHeader ? { ...authHeader } : undefined,
    })
      .then(async (res) => {
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`${res.status} ${res.statusText}: ${txt}`);
        }
        return res.json();
      })
      .then((data) => {
        if (!mounted) return;
        setUser(data);
        setForm({
          name: data.name || "",
          email: data.email || "",
          profile_pic: data.profile_pic || "",
        });
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || "Failed to fetch user");
      })
      .finally(() => {
        if (!mounted) return;
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [meEndpoint, authHeader]);

  function onChange(e) {
    const { name, value } = e.target;
    setForm((s) => ({ ...s, [name]: value }));
    setSuccess(null);
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!user || !user.id) {
      setError("No user loaded");
      return;
    }

    // compute diff: only send fields that changed
    const patch = {};
    if ((form.name || "") !== (user.name || "")) patch.name = form.name;
    if ((form.email || "") !== (user.email || "")) patch.email = form.email;
    if ((form.profile_pic || "") !== (user.profile_pic || "")) patch.profile_pic = form.profile_pic;

    if (Object.keys(patch).length === 0) {
      setSuccess("No changes to save");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${usersEndpointBase}/${user.id}`, {
        method: "PATCH",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(authHeader || {}),
        },
        body: JSON.stringify(patch),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${txt}`);
      }

      const updated = await res.json();
      setUser(updated);
      setForm({
        name: updated.name || "",
        email: updated.email || "",
        profile_pic: updated.profile_pic || "",
      });
      setSuccess("Profile updated successfully");
    } catch (err) {
      setError(err.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="bg-white rounded-2xl shadow p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 flex flex-col items-center">
          {loading ? (
            <div className="h-32 w-32 rounded-full bg-gray-100 animate-pulse" />
          ) : (
            <img
              src={form.profile_pic || "https://via.placeholder.com/150"}
              alt="profile"
              className="h-32 w-32 rounded-full object-cover shadow mb-4"
            />
          )}

          <div className="text-center">
            <h2 className="text-lg font-medium">{user?.name || "User"}</h2>
            <p className="text-sm text-gray-500">ID: {user?.id ?? "-"}</p>
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          className="md:col-span-2 flex flex-col gap-4"
          aria-busy={saving}
        >
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              name="name"
              value={form.name}
              onChange={onChange}
              className="mt-1 block w-full rounded-lg border-gray-200 shadow-sm p-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              name="email"
              value={form.email}
              onChange={onChange}
              className="mt-1 block w-full rounded-lg border-gray-200 shadow-sm p-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Profile picture URL</label>
            <input
              name="profile_pic"
              value={form.profile_pic}
              onChange={onChange}
              className="mt-1 block w-full rounded-lg border-gray-200 shadow-sm p-2"
            />
            <p className="text-xs text-gray-500 mt-1">You can paste an image URL here to update your avatar.</p>
          </div>

          <div className="flex items-center gap-3 mt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center px-4 py-2 rounded-xl bg-blue-600 text-white font-medium shadow hover:opacity-95 disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>

            <button
              type="button"
              onClick={() => {
                // reset to server state
                setForm({
                  name: user?.name || "",
                  email: user?.email || "",
                  profile_pic: user?.profile_pic || "",
                });
                setSuccess(null);
                setError(null);
              }}
              className="inline-flex items-center px-3 py-2 rounded-xl bg-gray-100 text-gray-700 shadow"
            >
              Reset
            </button>

            {success && <div className="ml-3 text-green-600">{success}</div>}
            {error && <div className="ml-3 text-red-600">{error}</div>}
          </div>

          <div className="text-xs text-gray-400 mt-2">
            Note: this component sends a <code>PATCH</code> request to <code>{usersEndpointBase}/&lt;id&gt;</code>.
          </div>
        </form>
      </div>
    </div>
  );
}
