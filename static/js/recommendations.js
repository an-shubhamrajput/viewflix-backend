/**
 * ViewFlix — Recommendation UI JavaScript
 * Handles API calls, rendering, and interactions.
 */

const API_BASE = '/api/recommendations';
const TMDB_IMG_BASE = 'https://image.tmdb.org/t/p/w342';
const TMDB_IMG_LARGE = 'https://image.tmdb.org/t/p/w500';
const PLACEHOLDER_IMG = 'https://via.placeholder.com/342x513/1a1a28/8b8ba3?text=No+Poster';

// State
let selectedGenres = [];
let allGenres = [];

// ============================================================
// UTILS
// ============================================================

function posterUrl(path, large = false) {
    if (!path) return PLACEHOLDER_IMG;
    const base = large ? TMDB_IMG_LARGE : TMDB_IMG_BASE;
    return path.startsWith('http') ? path : base + path;
}

function truncate(text, maxLen = 120) {
    if (!text) return '';
    return text.length > maxLen ? text.substring(0, maxLen) + '…' : text;
}

function formatGenres(genres) {
    if (!genres) return '';
    // If it's already an array
    if (Array.isArray(genres)) {
        return genres.map(g => typeof g === 'object' ? g.name : g).join(', ');
    }
    // If it's a string that looks like JSON array
    if (typeof genres === 'string' && genres.trim().startsWith('[')) {
        try {
            const parsed = JSON.parse(genres);
            if (Array.isArray(parsed)) {
                return parsed.map(g => typeof g === 'object' ? g.name : g).join(', ');
            }
        } catch (e) { /* not valid JSON, use as-is */ }
    }
    return genres;
}

function setApiStatus(ok) {
    const el = document.getElementById('apiStatus');
    if (ok) {
        el.innerHTML = '<i class="bi bi-circle-fill text-success me-1" style="font-size:0.5rem;"></i> API Connected';
    } else {
        el.innerHTML = '<i class="bi bi-circle-fill text-danger me-1" style="font-size:0.5rem;"></i> API Error';
    }
}

// ============================================================
// GENRE PICKER
// ============================================================

async function loadGenres() {
    try {
        const res = await fetch(`${API_BASE}/genres`);
        if (!res.ok) throw new Error('Failed to fetch genres');
        allGenres = await res.json();
        renderGenres();
        setApiStatus(true);
    } catch (err) {
        console.error('Error loading genres:', err);
        document.getElementById('genreLoading').innerHTML =
            '<i class="bi bi-exclamation-triangle text-danger me-2"></i> Failed to load genres. Is the API running?';
        setApiStatus(false);
    }
}

function renderGenres() {
    const container = document.getElementById('genreChips');
    const loading = document.getElementById('genreLoading');
    loading.style.display = 'none';

    container.innerHTML = allGenres.map(genre => {
        // Handle both plain strings and {id, name} objects
        const name = typeof genre === 'object' ? genre.name : genre;
        return `
            <span class="vf-genre-chip" data-genre="${name}" onclick="toggleGenre(this)">
                ${name}
            </span>
        `;
    }).join('');
}

function toggleGenre(el) {
    const genre = el.dataset.genre;
    el.classList.toggle('active');

    if (el.classList.contains('active')) {
        if (!selectedGenres.includes(genre)) selectedGenres.push(genre);
    } else {
        selectedGenres = selectedGenres.filter(g => g !== genre);
    }

    updateSelectedCount();
}

function updateSelectedCount() {
    const btn = document.getElementById('getRecommendationsBtn');
    const countEl = document.getElementById('selectedCount');

    btn.disabled = selectedGenres.length === 0;
    countEl.textContent = selectedGenres.length > 0
        ? `${selectedGenres.length} genre${selectedGenres.length > 1 ? 's' : ''} selected`
        : '';
}

// ============================================================
// TOP 10 MOVIES
// ============================================================

async function loadTopTen() {
    try {
        const res = await fetch(`${API_BASE}/top-ten`);
        if (!res.ok) throw new Error('Failed to fetch top 10');
        const movies = await res.json();
        renderTopTen(movies);
        setApiStatus(true);
    } catch (err) {
        console.error('Error loading top 10:', err);
        document.getElementById('topTenSkeleton').innerHTML =
            '<div class="vf-empty-state"><i class="bi bi-exclamation-circle"></i>Unable to load top movies</div>';
    }
}

function renderTopTen(movies) {
    const container = document.getElementById('topTenContainer');
    container.innerHTML = movies.map((m, idx) => `
        <div class="vf-movie-card" onclick="openMovieModal(${JSON.stringify(m).replace(/"/g, '&quot;')})">
            <span class="vf-rank-badge">${idx + 1}</span>
            <img class="vf-card-poster" src="${posterUrl(m.poster_path)}" alt="${m.title}" loading="lazy"
                onerror="this.src='${PLACEHOLDER_IMG}'">
            <div class="vf-card-info-bar">
                <div class="vf-card-info-title" title="${m.title}">${m.title}</div>
                <div class="vf-card-info-genre">${truncate(formatGenres(m.genres), 30)}</div>
            </div>
        </div>
    `).join('');
}

// ============================================================
// HOMEPAGE SECTIONS
// ============================================================

async function loadHomepage() {
    const sectionContainer = document.getElementById('homepageSections');
    sectionContainer.innerHTML = `
        <div class="vf-loader-overlay">
            <div class="spinner-border spinner-border-sm text-info" role="status"></div>
            Loading personalized sections...
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/homepage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_genres: selectedGenres,
                limit: 15
            })
        });

        if (!res.ok) throw new Error('Failed to fetch homepage');
        const data = await res.json();
        renderHomepageSections(data.sections);
    } catch (err) {
        console.error('Error loading homepage:', err);
        sectionContainer.innerHTML = `
            <div class="vf-empty-state">
                <i class="bi bi-exclamation-circle"></i>
                Unable to load homepage sections
            </div>
        `;
    }
}

function renderHomepageSections(sections) {
    const container = document.getElementById('homepageSections');

    if (!sections || Object.keys(sections).length === 0) {
        container.innerHTML = `
            <div class="vf-empty-state">
                <i class="bi bi-film"></i>
                No movies found for the selected genres. Try different genres!
            </div>
        `;
        return;
    }

    const sectionIcons = {
        'trending': 'bi-fire',
        'popular': 'bi-graph-up-arrow',
        'top': 'bi-star-fill',
        'new': 'bi-lightning-fill',
        'classic': 'bi-gem',
        'action': 'bi-lightning-charge-fill',
        'comedy': 'bi-emoji-laughing',
        'drama': 'bi-mask',
        'horror': 'bi-emoji-dizzy',
        'romance': 'bi-heart-fill',
        'sci': 'bi-rocket-takeoff',
    };

    function getIcon(name) {
        const lowerName = name.toLowerCase();
        for (const [key, icon] of Object.entries(sectionIcons)) {
            if (lowerName.includes(key)) return icon;
        }
        return 'bi-collection-play-fill';
    }

    container.innerHTML = Object.entries(sections).map(([name, movies]) => `
        <section class="vf-section">
            <div class="container-fluid px-4">
                <div class="vf-section-header">
                    <h2 class="vf-section-title">
                        <i class="${getIcon(name)} text-info me-2"></i>
                        ${name}
                    </h2>
                    <span class="vf-section-badge">${movies.length} movies</span>
                </div>
                <div class="vf-scroll-container">
                    ${movies.map(m => createScrollCard(m)).join('')}
                </div>
            </div>
        </section>
    `).join('');
}

function createScrollCard(m) {
    const movieJson = JSON.stringify(m).replace(/"/g, '&quot;');
    return `
        <div class="vf-movie-card" onclick="openMovieModal(${movieJson})">
            <img class="vf-card-poster" src="${posterUrl(m.poster_path)}" alt="${m.title}" loading="lazy"
                onerror="this.src='${PLACEHOLDER_IMG}'">
            <div class="vf-card-overlay">
                <div class="vf-card-title">${m.title}</div>
                <div class="vf-card-genres">${truncate(formatGenres(m.genres), 30)}</div>
            </div>
            <div class="vf-card-info-bar">
                <div class="vf-card-info-title" title="${m.title}">${m.title}</div>
                <div class="vf-card-info-genre">${truncate(formatGenres(m.genres), 30)}</div>
            </div>
        </div>
    `;
}

// ============================================================
// RECOMMENDED FOR YOU
// ============================================================

async function loadRecommendedForYou() {
    const section = document.getElementById('recoSection');
    const container = document.getElementById('recoContainer');
    section.style.display = 'block';
    container.innerHTML = `
        <div class="col-12 vf-loader-overlay">
            <div class="spinner-border spinner-border-sm text-info" role="status"></div>
            Generating recommendations...
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/recommended-for-you`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_genres: selectedGenres,
                limit: 24
            })
        });

        if (!res.ok) throw new Error('Failed to fetch recommendations');
        const movies = await res.json();
        renderRecommended(movies);
    } catch (err) {
        console.error('Error loading recommendations:', err);
        container.innerHTML = `
            <div class="col-12 vf-empty-state">
                <i class="bi bi-exclamation-circle"></i>
                Unable to load recommendations
            </div>
        `;
    }
}

function renderRecommended(movies) {
    const container = document.getElementById('recoContainer');

    if (!movies || movies.length === 0) {
        container.innerHTML = `
            <div class="col-12 vf-empty-state">
                <i class="bi bi-film"></i>
                No recommendations found. Try different genres!
            </div>
        `;
        return;
    }

    container.innerHTML = movies.map(m => {
        const movieJson = JSON.stringify(m).replace(/"/g, '&quot;');
        return `
            <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                <div class="vf-grid-card" onclick="openMovieModal(${movieJson})">
                    <img class="vf-grid-poster" src="${posterUrl(m.poster_path)}" alt="${m.title}" loading="lazy"
                        onerror="this.src='${PLACEHOLDER_IMG}'">
                    <div class="vf-grid-card-body">
                        <div class="vf-grid-card-title">${m.title}</div>
                        <div class="vf-grid-card-genres">${truncate(formatGenres(m.genres), 35)}</div>
                        <div class="vf-grid-card-overview">${truncate(m.overview, 100)}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================
// MOVIE MODAL & MORE LIKE THIS
// ============================================================

function openMovieModal(movie) {
    document.getElementById('modalTitle').textContent = movie.title;
    document.getElementById('modalPoster').src = posterUrl(movie.poster_path, true);
    document.getElementById('modalPoster').alt = movie.title;
    document.getElementById('modalOverview').textContent = movie.overview || 'No overview available.';

    // Genres
    const genreStr = formatGenres(movie.genres);
    const genresArr = genreStr.split(',').map(g => g.trim()).filter(Boolean);
    document.getElementById('modalGenres').innerHTML = genresArr.map(g =>
        `<span class="vf-modal-genre-badge">${g}</span>`
    ).join('');

    // Meta
    const metaParts = [];
    if (movie.popularity) metaParts.push(`⭐ ${Number(movie.popularity).toFixed(1)} popularity`);
    if (movie.release_date) metaParts.push(`📅 ${movie.release_date}`);
    if (movie.source_db) metaParts.push(`💾 ${movie.source_db}`);
    document.getElementById('modalMeta').textContent = metaParts.join('  •  ');

    // More Like This
    const mltSection = document.getElementById('moreLikeThisSection');
    const mltContainer = document.getElementById('moreLikeThisContainer');
    mltSection.style.display = 'none';
    mltContainer.innerHTML = '';

    if (movie.id) {
        loadMoreLikeThis(movie.id);
    }

    const modal = new bootstrap.Modal(document.getElementById('movieModal'));
    modal.show();
}

async function loadMoreLikeThis(movieId) {
    const section = document.getElementById('moreLikeThisSection');
    const container = document.getElementById('moreLikeThisContainer');

    section.style.display = 'block';
    container.innerHTML = `
        <div class="vf-loader-overlay" style="padding:1rem;">
            <div class="spinner-border spinner-border-sm text-info" role="status"></div>
            Finding similar movies...
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/more-like-this/${movieId}?limit=10`);
        if (!res.ok) throw new Error('Failed to fetch similar movies');
        const movies = await res.json();

        if (movies.length === 0) {
            section.style.display = 'none';
            return;
        }

        container.innerHTML = movies.map(m => createScrollCard(m)).join('');
    } catch (err) {
        console.error('Error loading more like this:', err);
        container.innerHTML = `
            <div class="vf-empty-state" style="padding:1rem;">
                <small class="text-secondary">Similar movies unavailable</small>
            </div>
        `;
    }
}

// ============================================================
// GET RECOMMENDATIONS BUTTON
// ============================================================

document.getElementById('getRecommendationsBtn').addEventListener('click', async () => {
    if (selectedGenres.length === 0) return;

    const btn = document.getElementById('getRecommendationsBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Loading...';

    await Promise.all([
        loadHomepage(),
        loadRecommendedForYou()
    ]);

    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-magic me-2"></i> Get Recommendations';
});

// ============================================================
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    loadGenres();
    loadTopTen();
});
