import { useNavigate } from 'react-router-dom';
import type { Team } from '../types';
import './TeamCard.css';

interface Props {
    team: Team;
}

export default function TeamCard({ team }: Props) {
    const navigate = useNavigate();

    return (
        <div className="team-card" onClick={() => navigate(`/teams/${team.id}`, { state: { teamName: team.name } })}>
            <div className="team-card__logo">
                {team.logoPath
                    ? <img src={team.logoPath} alt={team.name} />
                    : <div className="team-card__logo-placeholder" />}
            </div>
            <div className="team-card__name">{team.name}</div>
        </div>
    );
}
