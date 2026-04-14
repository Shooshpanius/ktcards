import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import type { Season, Team } from '../types';
import { csrfFetch } from '../csrf';
import './AdminPage.css';

export default function AdminPage() {
    const [authenticated, setAuthenticated] = useState<boolean | null>(null);
    const [passwordInput, setPasswordInput] = useState('');
    const [passwordError, setPasswordError] = useState('');

    useEffect(() => {
        fetch('/api/auth/check')
            .then(r => setAuthenticated(r.ok))
            .catch(() => setAuthenticated(false));
    }, []);

    async function handleLogin(e: React.FormEvent) {
        e.preventDefault();
        setPasswordError('');
        try {
            const r = await csrfFetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: passwordInput }),
            });
            if (r.ok) {
                setAuthenticated(true);
            } else {
                setPasswordError('Неверный пароль.');
            }
        } catch {
            setPasswordError('Ошибка соединения с сервером.');
        }
    }

    if (authenticated === null) {
        return null;
    }

    if (!authenticated) {
        return (
            <div className="admin">
                <header className="admin__header">
                    <Link to="/" className="admin__back">← Back</Link>
                    <h1 className="admin__title">Admin Panel</h1>
                </header>
                <div className="admin__login">
                    <form onSubmit={handleLogin} className="admin__form">
                        <input
                            className="admin__input"
                            type="password"
                            placeholder="Пароль"
                            value={passwordInput}
                            onChange={e => setPasswordInput(e.target.value)}
                            autoFocus
                            required
                        />
                        <button className="admin__btn admin__btn--primary" type="submit">Войти</button>
                    </form>
                    {passwordError && <p className="admin__error">{passwordError}</p>}
                </div>
            </div>
        );
    }

    return <AdminContent onLogout={() => setAuthenticated(false)} />;
}

function AdminContent({ onLogout }: { onLogout: () => void }) {
    const [seasons, setSeasons] = useState<Season[]>([]);
    const [newSeasonName, setNewSeasonName] = useState('');
    const [seasonError, setSeasonError] = useState('');

    const [newTeamName, setNewTeamName] = useState('');
    const [newTeamSeasonId, setNewTeamSeasonId] = useState<number | ''>('');
    const [newTeamLogo, setNewTeamLogo] = useState<File | null>(null);
    const [teamError, setTeamError] = useState('');
    const logoInputRef = useRef<HTMLInputElement>(null);

    const [allTeams, setAllTeams] = useState<Team[]>([]);

    useEffect(() => {
        loadSeasons();
        loadTeams();
    }, []);

    async function loadSeasons() {
        const r = await fetch('/api/seasons');
        if (r.ok) setSeasons(await r.json());
    }

    async function loadTeams() {
        const r = await fetch('/api/teams');
        if (r.ok) setAllTeams(await r.json());
    }

    async function addSeason(e: React.FormEvent) {
        e.preventDefault();
        setSeasonError('');
        const r = await csrfFetch('/api/seasons', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newSeasonName }),
        });
        if (r.ok) {
            setNewSeasonName('');
            await loadSeasons();
        } else {
            const msg = await r.text();
            setSeasonError(msg || 'Failed to create season.');
        }
    }

    async function deleteSeason(id: number) {
        if (!confirm('Delete this season and all its teams?')) return;
        await csrfFetch(`/api/seasons/${id}`, { method: 'DELETE' });
        await loadSeasons();
        await loadTeams();
    }

    async function addTeam(e: React.FormEvent) {
        e.preventDefault();
        setTeamError('');
        if (!newTeamSeasonId) {
            setTeamError('Please select a season.');
            return;
        }
        const form = new FormData();
        form.append('name', newTeamName);
        form.append('seasonId', String(newTeamSeasonId));
        if (newTeamLogo) form.append('logo', newTeamLogo);
        const r = await csrfFetch('/api/teams', { method: 'POST', body: form });
        if (r.ok) {
            setNewTeamName('');
            setNewTeamSeasonId('');
            setNewTeamLogo(null);
            if (logoInputRef.current) logoInputRef.current.value = '';
            await loadSeasons();
            await loadTeams();
        } else {
            const msg = await r.text();
            setTeamError(msg || 'Failed to create team.');
        }
    }

    async function deleteTeam(id: number) {
        if (!confirm('Delete this team?')) return;
        await csrfFetch(`/api/teams/${id}`, { method: 'DELETE' });
        await loadSeasons();
        await loadTeams();
    }

    async function importTeamCards(id: number, _name: string) {
        const r = await csrfFetch(`/api/teams/${id}/cards/import`, { method: 'POST' });
        if (r.ok) {
            const data = await r.json();
            alert(data.message ?? 'Import successful.');
        } else {
            const msg = await r.text();
            alert(`Import failed: ${msg}`);
        }
    }

    const seasonById = Object.fromEntries(seasons.map(s => [s.id, s.name]));

    async function handleLogout() {
        await csrfFetch('/api/auth/logout', { method: 'POST' });
        onLogout();
    }

    return (
        <div className="admin">
            <header className="admin__header">
                <Link to="/" className="admin__back">← Back</Link>
                <h1 className="admin__title">Admin Panel</h1>
                <button className="admin__btn admin__btn--secondary" onClick={handleLogout}>Выйти</button>
            </header>

            <div className="admin__columns">
                {/* Seasons management */}
                <section className="admin__section">
                    <h2>Seasons</h2>
                    <form onSubmit={addSeason} className="admin__form">
                        <input
                            className="admin__input"
                            type="text"
                            placeholder="Season name"
                            value={newSeasonName}
                            onChange={e => setNewSeasonName(e.target.value)}
                            required
                        />
                        <button className="admin__btn admin__btn--primary" type="submit">Add Season</button>
                    </form>
                    {seasonError && <p className="admin__error">{seasonError}</p>}

                    <ul className="admin__list">
                        {seasons.map(s => (
                            <li key={s.id} className="admin__list-item">
                                <span>{s.name}</span>
                                <button
                                    className="admin__btn admin__btn--danger"
                                    onClick={() => deleteSeason(s.id)}
                                >Delete</button>
                            </li>
                        ))}
                        {seasons.length === 0 && <li className="admin__list-empty">No seasons yet.</li>}
                    </ul>
                </section>

                {/* Teams management */}
                <section className="admin__section">
                    <h2>Teams</h2>
                    <form onSubmit={addTeam} className="admin__form admin__form--column">
                        <input
                            className="admin__input"
                            type="text"
                            placeholder="Team name"
                            value={newTeamName}
                            onChange={e => setNewTeamName(e.target.value)}
                            required
                        />
                        <select
                            className="admin__input"
                            value={newTeamSeasonId}
                            onChange={e => setNewTeamSeasonId(Number(e.target.value))}
                            required
                        >
                            <option value="">Select season…</option>
                            {seasons.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                        <label className="admin__file-label">
                            <span>Logo (optional)</span>
                            <input
                                ref={logoInputRef}
                                type="file"
                                accept="image/*"
                                onChange={e => setNewTeamLogo(e.target.files?.[0] ?? null)}
                            />
                        </label>
                        <button className="admin__btn admin__btn--primary" type="submit">Add Team</button>
                    </form>
                    {teamError && <p className="admin__error">{teamError}</p>}

                    <ul className="admin__list">
                        {allTeams.map(t => (
                            <li key={t.id} className="admin__list-item">
                                {t.logoPath && (
                                    <img className="admin__team-logo" src={t.logoPath} alt={t.name} />
                                )}
                                <span>
                                    <strong>{t.name}</strong>
                                    <em> — {seasonById[t.seasonId] ?? `Season ${t.seasonId}`}</em>
                                </span>
                                <button
                                    className="admin__btn admin__btn--secondary"
                                    onClick={() => importTeamCards(t.id, t.name)}
                                    title={`Загрузить данные из файла ${t.name}.bd`}
                                >Загрузить данные из файла</button>
                                <button
                                    className="admin__btn admin__btn--danger"
                                    onClick={() => deleteTeam(t.id)}
                                >Delete</button>
                            </li>
                        ))}
                        {allTeams.length === 0 && <li className="admin__list-empty">No teams yet.</li>}
                    </ul>
                </section>
            </div>
        </div>
    );
}
