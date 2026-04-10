import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import type {
    TeamCards,
    Operative,
    FactionRule,
    MarkerToken,
    StrategyPloy,
    FirefightPloy,
    FactionEquipment,
} from '../types';
import './TeamCardsPage.css';

export default function TeamCardsPage() {
    const { teamId } = useParams<{ teamId: string }>();
    const location = useLocation();
    const navigate = useNavigate();
    const teamName: string = (location.state as { teamName?: string } | null)?.teamName ?? `Team #${teamId}`;

    const [cards, setCards] = useState<TeamCards | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetch(`/api/teams/${teamId}/cards`)
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then((data: TeamCards) => {
                setCards(data);
                setLoading(false);
            })
            .catch((err: unknown) => {
                console.error('Failed to load cards:', err);
                setError('Failed to load cards. Please try again later.');
                setLoading(false);
            });
    }, [teamId]);

    return (
        <div className="tcpage">
            <header className="tcpage__header">
                <button className="tcpage__back" onClick={() => navigate(-1)}>← Back</button>
                <h1 className="tcpage__title">{teamName}</h1>
            </header>

            {loading && <p className="tcpage__status">Loading...</p>}
            {error && <p className="tcpage__status tcpage__status--error">{error}</p>}

            {cards && (
                <div className="tcpage__sections">
                    {cards.operatives.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Operatives</h2>
                            <div className="tcpage__cards">
                                {cards.operatives.map(op => <OperativeCard key={op.id} op={op} />)}
                            </div>
                        </section>
                    )}

                    {cards.factionRules.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Faction Rules</h2>
                            <div className="tcpage__cards">
                                {cards.factionRules.map(r => <SimpleCard key={r.id} item={r} />)}
                            </div>
                        </section>
                    )}

                    {cards.markerTokens.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Markers &amp; Tokens</h2>
                            <div className="tcpage__cards">
                                {cards.markerTokens.map(m => <SimpleCard key={m.id} item={m} />)}
                            </div>
                        </section>
                    )}

                    {cards.strategyPloys.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Strategy Ploys</h2>
                            <div className="tcpage__cards">
                                {cards.strategyPloys.map(p => <PloyCard key={p.id} item={p} costLabel="CP" cost={p.cpCost} />)}
                            </div>
                        </section>
                    )}

                    {cards.firefightPloys.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Firefight Ploys</h2>
                            <div className="tcpage__cards">
                                {cards.firefightPloys.map(p => <PloyCard key={p.id} item={p} costLabel="CP" cost={p.cpCost} />)}
                            </div>
                        </section>
                    )}

                    {cards.factionEquipment.length > 0 && (
                        <section className="tcpage__section">
                            <h2 className="tcpage__section-title">Faction Equipment</h2>
                            <div className="tcpage__cards">
                                {cards.factionEquipment.map(e => <EquipmentCard key={e.id} item={e} />)}
                            </div>
                        </section>
                    )}

                    {cards.operatives.length === 0 &&
                        cards.factionRules.length === 0 &&
                        cards.markerTokens.length === 0 &&
                        cards.strategyPloys.length === 0 &&
                        cards.firefightPloys.length === 0 &&
                        cards.factionEquipment.length === 0 && (
                            <p className="tcpage__status">No cards imported for this team yet.</p>
                        )}
                </div>
            )}
        </div>
    );
}

function OperativeCard({ op }: { op: Operative }) {
    return (
        <div className="op-card">
            <div className="op-card__header">
                <span className="op-card__name">{op.name}</span>
                {op.keywords && <span className="op-card__keywords">{op.keywords}</span>}
            </div>
            <div className="op-card__stats">
                <Stat label="M" value={op.movement ?? '—'} />
                <Stat label="APL" value={op.actionPointLimit} />
                <Stat label="GA" value={op.groupActivations} />
                <Stat label="DF" value={op.defence} />
                <Stat label="SV" value={op.save} />
                <Stat label="W" value={op.wounds} />
            </div>

            {op.attacks.length > 0 && (
                <table className="op-card__attacks">
                    <thead>
                        <tr>
                            <th>Weapon</th>
                            <th>Type</th>
                            <th>A</th>
                            <th>BS/WS</th>
                            <th>D</th>
                            <th>CD</th>
                            <th>SR</th>
                        </tr>
                    </thead>
                    <tbody>
                        {op.attacks.map(a => (
                            <tr key={a.id}>
                                <td>{a.name}</td>
                                <td>{a.attackType}</td>
                                <td>{a.attacks}</td>
                                <td>{a.hitSkill}+</td>
                                <td>{a.damage}</td>
                                <td>{a.criticalDamage}</td>
                                <td>{a.specialRules ?? '—'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {op.abilities.length > 0 && (
                <div className="op-card__abilities">
                    {op.abilities.map(ab => (
                        <div key={ab.id} className="op-card__ability">
                            <span className="op-card__ability-name">{ab.name}:</span>{' '}
                            <span>{ab.description}</span>
                        </div>
                    ))}
                </div>
            )}

            {op.notes && <div className="op-card__notes">{op.notes}</div>}
        </div>
    );
}

function Stat({ label, value }: { label: string; value: string | number }) {
    return (
        <div className="stat">
            <div className="stat__value">{value}</div>
            <div className="stat__label">{label}</div>
        </div>
    );
}

function SimpleCard({ item }: { item: FactionRule | MarkerToken }) {
    return (
        <div className="dc-card">
            <div className="dc-card__name">{item.name}</div>
            <div className="dc-card__desc">{item.description}</div>
        </div>
    );
}

function PloyCard({ item, costLabel, cost }: { item: StrategyPloy | FirefightPloy; costLabel: string; cost: number }) {
    return (
        <div className="dc-card">
            <div className="dc-card__header">
                <span className="dc-card__name">{item.name}</span>
                <span className="dc-card__cost">{cost} {costLabel}</span>
            </div>
            <div className="dc-card__desc">{item.description}</div>
        </div>
    );
}

function EquipmentCard({ item }: { item: FactionEquipment }) {
    return (
        <div className="dc-card">
            <div className="dc-card__header">
                <span className="dc-card__name">{item.name}</span>
                <span className="dc-card__cost">{item.epCost} EP</span>
            </div>
            <div className="dc-card__desc">{item.description}</div>
            {item.restrictions && (
                <div className="dc-card__restrictions">Restrictions: {item.restrictions}</div>
            )}
        </div>
    );
}
