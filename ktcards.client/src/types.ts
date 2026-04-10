export interface Team {
    id: number;
    name: string;
    logoPath: string | null;
    seasonId: number;
}

export interface Season {
    id: number;
    name: string;
    teams: Team[];
}

export interface OperativeAbility {
    id: number;
    name: string;
    description: string;
}

export interface OperativeAttack {
    id: number;
    name: string;
    attackType: string;
    attacks: number;
    hitSkill: number;
    damage: string;
    criticalDamage: string;
    specialRules: string | null;
}

export interface Operative {
    id: number;
    teamId: number;
    name: string;
    keywords: string | null;
    movement: string | null;
    actionPointLimit: number;
    groupActivations: number;
    defence: number;
    save: number;
    wounds: number;
    notes: string | null;
    abilities: OperativeAbility[];
    attacks: OperativeAttack[];
}

export interface FactionRule {
    id: number;
    teamId: number;
    name: string;
    description: string;
}

export interface MarkerToken {
    id: number;
    teamId: number;
    name: string;
    description: string;
}

export interface StrategyPloy {
    id: number;
    teamId: number;
    name: string;
    cpCost: number;
    description: string;
}

export interface FirefightPloy {
    id: number;
    teamId: number;
    name: string;
    cpCost: number;
    description: string;
}

export interface FactionEquipment {
    id: number;
    teamId: number;
    name: string;
    epCost: number;
    description: string;
    restrictions: string | null;
}

export interface TeamCards {
    operatives: Operative[];
    factionRules: FactionRule[];
    markerTokens: MarkerToken[];
    strategyPloys: StrategyPloy[];
    firefightPloys: FirefightPloy[];
    factionEquipment: FactionEquipment[];
}

