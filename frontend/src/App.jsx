import { useState } from 'react';
import './App.css';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Factoid Builder</h1>
        <p>React frontend is successfully connected to Django!</p>
        <button onClick={() => setCount((count) => count + 1)}>
          Click count: {count}
        </button>
        <p style={{ marginTop: '20px', fontSize: '14px', opacity: 0.8 }}>
          This is where the new factoid system will be built.
        </p>
      </header>
    </div>
  );
}

export default App;
