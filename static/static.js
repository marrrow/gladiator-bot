const tg = window.Telegram.WebApp;
const duelId = new URLSearchParams(window.location.search).get('id');
const socket = io();

tg.ready();

socket.on('connect', () => {
    socket.emit('connect', {
        duel_id: duelId,
        user_id: tg.initDataUnsafe.user.id
    });
});

socket.on('update', players => {
    const container = document.getElementById('players');
    container.innerHTML = '';
    for (const [id, stats] of Object.entries(players)) {
        container.innerHTML += `
            <div class="player">
                <div>${id}</div>
                <div class="health" style="width: ${stats.health}%"></div>
            </div>
        `;
    }
});

socket.on('winner', data => {
    alert(`Winner: ${data.winner}!`);
    tg.close();
});

function attack() {
    socket.emit('attack', {
        duel_id: duelId,
        user_id: tg.initDataUnsafe.user.id
    });
}