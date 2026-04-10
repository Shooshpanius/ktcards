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
