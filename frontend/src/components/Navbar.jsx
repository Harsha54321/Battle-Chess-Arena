import { Link } from "react-router-dom";
import "../styles/navbar.css";

function Navbar() {
  return (
    <nav className="navbar">
      <div className="logo">Battle Chess Arena</div>

      <div className="nav-links">
        <Link to="/">Home</Link>
        <Link to="/game">Game</Link>
        <Link to="/login">Login</Link>
        <Link to="/profile">Profile</Link>
      </div>
    </nav>
  );
}

export default Navbar;