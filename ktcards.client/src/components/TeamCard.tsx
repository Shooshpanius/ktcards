import type { Team } from '../types';
import './TeamCard.css';

interface Props {
    team: Team;
}

export default function TeamCard({ team }: Props) {
    return (
        <div className="team-card">
            <div className="team-card__logo">
                {team.logoPath
                    ? <img src={team.logoPath} alt={team.name} />
                    : <div className="team-card__logo-placeholder" />}
            </div>
            <div className="team-card__name">{team.name}</div>
        </div>
    );
}
