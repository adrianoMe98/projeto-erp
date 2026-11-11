export type Papel = "admin" | "operador" | "cliente";
export type Cliente = {
  id: string;
  nome_fantasia: string;
  razao_social: string;
  cnpj: string;
  contato_principal: string;
  email: string;
  telefone: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
};
export type ClienteInput = Omit<Cliente, "id" | "created_at" | "updated_at">;
export type Perfil = {
  id: string;
  nome: string;
  papel: Papel;
  cliente_id: string | null;
};
export type Database = {
  public: {
    Tables: {
      clientes: {
        Row: Cliente;
        Insert: ClienteInput & {
          id?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<ClienteInput>;
        Relationships: [];
      };
      perfis: {
        Row: Perfil;
        Insert: Perfil;
        Update: Partial<Perfil>;
        Relationships: [];
      };
    };
    Views: { [_ in never]: never };
    Functions: { [_ in never]: never };
    Enums: { papel_erp: Papel };
    CompositeTypes: { [_ in never]: never };
  };
};
