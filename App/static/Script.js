async function startImportProcess() {
  await openAuthorizationUrl();
  checkAuthorizationStatus();
}

function checkAuthorizationStatus() {
  // Polling every 5 seconds to check if authorization is complete
  const interval = setInterval(async () => {
    const response = await fetch('/check_authorization');
    const { authorized } = await response.json();

    console.log(`check authorization status: ${authorized}`);

    if (authorized) {
      clearInterval(interval);
      getCollection(); // Fetch and display the collection
    }
  }, 5000);
}

function getCollection() {
  console.log(`Fetching collection`);

  fetch(`http://127.0.0.1:5000/get_collection`)
    .then((response) => response.json())
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      // Update the UI with the data
      const albumList = document.getElementById('album-list');
      albumList.innerHTML = ''; // Clear previous data

      data
        .forEach((album) => {
          const listItem = document.createElement('li');
          listItem.textContent = `${album.artist} - ${album.title}`;
          albumList.appendChild(listItem);
        })
        .catch((error) => {
          console.error('Fetch error:', error.message);
        });
    });
}

async function openAuthorizationUrl() {
  const response = await fetch('/authorize_discogs', { method: 'POST' });
  const data = await response.json();

  console.log(data);
  console.log(data.authorize_url);
  // Update the UI with the authorization URL

  // Open the URL in a new tab or window
  window.open(data.authorize_url, '_blank');

  console.log('open auth URL');
}

function logoutUser() {
  fetch('/logout')
    .then((response) => {
      if (response.ok) {
        console.log('User logged out');
        // Optionally, refresh the page or redirect the user to the home page
        window.location.href = '/';
      }
    })
    .catch((error) => console.error('Error logging out:', error));
}
