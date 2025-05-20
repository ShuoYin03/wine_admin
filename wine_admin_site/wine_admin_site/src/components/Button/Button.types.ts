export type ButtonMode = 'primary' | 'outline' | 'dashed' | 'ghost';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  mode?: ButtonMode;
  children: React.ReactNode;
}