import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import TeamCard from '../components/TeamCard';
import type { Season } from '../types';
import './HomePage.css';

export default function HomePage() {
    const [seasons, setSeasons] = useState<Season[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/seasons')
            .then(r => r.json())
            .then((data: Season[]) => {
                setSeasons(data);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    return (
        <div className="home">
            <header className="home__header">
                <h1 className="home__title">KillTeam Cards</h1>
                <Link to="/admin" className="home__admin-link">Admin</Link>
            </header>

            {loading && <p className="home__loading">Loading...</p>}

            {!loading && seasons.length === 0 && (
                <p className="home__empty">No seasons yet. <Link to="/admin">Add one in Admin.</Link></p>
            )}

            <div className="home__seasons">
                {seasons.map(season => (
                    <section key={season.id} className="home__season-section">
                        <div className="season-divider">
                            <div className="season-divider__line" />
                            <span className="season-divider__label">{season.name}</span>
                            <div className="season-divider__line" />
                        </div>
                        <div className="home__cards">
                            {season.teams.length === 0 && (
                                <p className="home__empty">No teams in this season yet.</p>
                            )}
                            {season.teams.map(team => (
                                <TeamCard key={team.id} team={team} />
                            ))}
                        </div>
                    </section>
                ))}
            </div>
        </div>
    );
}
