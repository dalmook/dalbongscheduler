interface SearchBarProps {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}

function SearchBar({ value, onChange, placeholder = "Search" }: SearchBarProps) {
  return <input className="input" value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />;
}

export default SearchBar;
