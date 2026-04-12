import { useEffect, useState } from 'react';
import TeamCard from '../components/TeamCard';
import type { Season } from '../types';
import { VERSION } from '../version';
import './HomePage.css';

export default function HomePage() {
    const [seasons, setSeasons] = useState<Season[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetch('/api/seasons')
            .then(r => r.json())
            .then((data: Season[]) => {
                setSeasons(data);
                setLoading(false);
            })
            .catch((err: unknown) => {
                console.error('Failed to load seasons:', err);
                setError('Failed to load data. Please try again later.');
                setLoading(false);
            });
    }, []);

    return (
        <div className="home">
            <header className="home__header">
                <h1 className="home__title">KillTeam Cards</h1>
                <span className="home__version">{VERSION}</span>
            </header>

            {loading && <p className="home__loading">Loading...</p>}
            {error && <p className="home__error">{error}</p>}

            {!loading && seasons.length === 0 && (
                <p className="home__empty">No seasons yet.</p>
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
