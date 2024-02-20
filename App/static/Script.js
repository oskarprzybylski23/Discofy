async function startImportProcess() {
  const response = await fetch('/check_authorization');
  const { authorized } = await response.json();

  if (authorized) {
    console.log('Already authorized. Fetching collection.');
    getCollection(); // Directly fetch and display the collection
  } else {
    console.log('Not authorized. Opening authorization URL.');
    await openAuthorizationUrl();
    checkAuthorizationStatus(); // Start polling for authorization status
  }
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

  // Specify dimensions and features for the modal window
  const width = 500; // Width of the window
  const height = 600; // Height of the window
  const left = (window.innerWidth - width) / 2; // Center the window horizontally
  const top = (window.innerHeight - height) / 2; // Center the window vertically

  const features = `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`;

  window.open(data.authorize_url, 'authWindow', features); // Open the URL in a new tab or window
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

window.addEventListener(
  'message',
  (event) => {
    if (event.data === 'authorizationComplete') {
      console.log(
        'Discogs authorization completed. Proceeding with next steps.'
      );
      // Close modal if you have one open
      // Refresh data or UI as necessary
    }
  },
  false
);