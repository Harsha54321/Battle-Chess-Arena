import React from 'react'

function Layout({ children }) {
  return (
    <div
      style={{
        maxWidth: "1400px",
        margin: "0 auto",
        padding: "20px",
      }}
    >
      {children}
    </div>
  );
}

export default Layout;
