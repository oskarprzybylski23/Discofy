async function startImportProcess() {
  await openAuthorizationUrl();
  checkAuthorizationStatus();
}

function displayCollection(data) {
  const albumList = document.getElementById('collection-list');
  albumList.innerHTML = ''; // Clear previous data

  data.forEach((album) => {
    const listItem = document.createElement('li');
    listItem.textContent = `${album.index}. ${album.artist} - ${album.title}`;
    listItem.id = `${album.discogs_id}`;
    listItem.className = 'collection-item';
    albumList.appendChild(listItem);
  });
}

function checkAuthorizationStatus() {
  // Polling every 5 seconds to check if authorization is complete
  const interval = setInterval(async () => {
    const response = await fetch('/check_authorization');
    const { authorized } = await response.json();

    console.log(`check authorization status: ${authorized}`);

    if (authorized) {
      clearInterval(interval);
      getCollection(); // Fetch the collection
    }
  }, 5000);
}

function getCollection() {
  console.log(`Fetching collection`);

  fetch(`http://127.0.0.1:5000/get_collection`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      displayCollection(data); // Update the UI with the data
    })
    .catch((error) => {
      console.error('Fetch error:', error.message);
    });
}

async function openAuthorizationUrl() {
  const response = await fetch('/authorize_discogs', { method: 'POST' });
  const data = await response.json();

  window.open(data.authorize_url, '_blank'); // Open the URL in a new tab or window
}

// Clear user tokens
function logoutUser() {
  fetch('/logout')
    .then((response) => {
      if (response.ok) {
        console.log('User logged out');
      }
    })
    .catch((error) => console.error('Error logging out:', error));
}
