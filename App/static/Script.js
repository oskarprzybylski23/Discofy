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
  const authorizeUrlElement = document.getElementById('authorize-url');
  authorizeUrlElement.textContent = data.authorize_url;

  // Open the URL in a new tab or window
  window.open(data.authorize_url, '_blank');

  console.log('open auth URL');
}
