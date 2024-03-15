// ---- DISCOGS ----

async function startImportProcess() {
  const response = await fetch('/check_authorization');
  const { authorized } = await response.json();

  if (authorized) {
    console.log('Already authorized. Fetching collection.');
    enableLogoutButton();
    getLibrary(); // Directly fetch and display the collection
  } else {
    console.log('Not authorized. Opening authorization URL.');
    await openAuthorizationUrl();
    checkAuthorizationStatus(); // Start polling for authorization status
  }
}

function returnToLibrary() {
  toggleReturnButton(false);
  getLibrary();
}

function displayLibrary(data) {
  // Change later to rember data so no repeat fetch is required if library is to be displayed again.
  const libraryList = document.getElementById('list-discogs');
  libraryList.innerHTML = ''; // Clear previous data

  const template = document.getElementById('folderTemplate');

  data.forEach((folder, index) => {
    const clone = document.importNode(template.content, true);
    // Now you can find and populate the specific parts of the template
    clone.querySelector('.folder-index').textContent = `${index + 1}`;
    clone.querySelector('.folder-name').textContent = folder.folder;
    clone.querySelector('.folder-count').textContent = folder.count;

    // Set the ID on the <li> for reference
    const listItem = clone.querySelector('li');
    listItem.id = `folder-${index}`;

    listItem.addEventListener('click', () => getCollection(index));

    libraryList.appendChild(clone);
  });
}

function displayCollection(data) {
  const albumList = document.getElementById('list-discogs');
  albumList.innerHTML = ''; // Clear previous data

  const template = document.getElementById('albumTemplate');

  data.forEach((album, index) => {
    const clone = document.importNode(template.content, true);

    // Now you can find and populate the specific parts of the template
    clone.querySelector('.album-index').textContent = `${index + 1}`;
    clone.querySelector('.album-artist').textContent = album.artist;
    clone.querySelector('.album-title').textContent = album.title;
    clone.querySelector('.album-cover').setAttribute('src', album.cover);

    // Set the ID on the <li> for reference
    const listItem = clone.querySelector('li');
    listItem.id = `${album.discogs_id}`;

    albumList.appendChild(clone);
  });
  toggleReturnButton(true);
}

function displayPlaylist(data) {
  // Change later to rember data so no repeat fetch is required if library is to be displayed again.
  const PlaylistList = document.getElementById('list-spotify');
  PlaylistList.innerHTML = ''; // Clear previous data

  const template = document.getElementById('albumTemplate');

  data.forEach((album, index) => {
    if (album.found) {
      const clone = document.importNode(template.content, true);

      // Now you can find and populate the specific parts of the template
      clone.querySelector('.album-index').textContent = `${index + 1}`;
      clone.querySelector('.album-artist').textContent = album.artist;
      clone.querySelector('.album-title').textContent = album.title;
      clone.querySelector('.album-cover').setAttribute('src', album.image);

      // Set the ID on the <li> for reference
      const listItem = clone.querySelector('li');
      listItem.id = `${album.discogs_id}`;

      PlaylistList.appendChild(clone);
    } else {
      const albumElementInLibrary = document.querySelector(
        `#list-discogs li[id="${album.discogs_id}"] .album`
      );

      if (albumElementInLibrary) {
        // Add a class to highlight the album, ensure you define this class in your CSS
        albumElementInLibrary.classList.add('not-found-highlight');
      }
    }
  });
}

function checkAuthorizationStatus() {
  // Polling every 5 seconds to check if authorization is complete
  const interval = setInterval(async () => {
    const response = await fetch('/check_authorization');
    const { authorized } = await response.json();

    console.log(`check authorization status: ${authorized}`);

    if (authorized) {
      enableLogoutButton();
      clearInterval(interval);
      getLibrary(); // Fetch the collection
    }
  }, 5000);
}

function getLibrary() {
  console.log(`Fetching folders`);
  showSpinner('loading-spinner-discogs', 'Fetching your library');
  fetch(`http://127.0.0.1:5000/get_library`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      hideSpinner('loading-spinner-discogs');
      const userInfo = document.getElementById('user-info-discogs');
      userInfo.display = 'block';
      userInfo.querySelector('a').textContent = data.user_info.username;
      userInfo.querySelector('a').href = data.user_info.url;
      displayLibrary(data.library); // Update the UI with the data
    })
    .catch((error) => {
      console.error('Fetch error:', error.message);
    });
}

function getCollection(folder) {
  console.log(`Fetching collection for folder ${folder}`);
  showSpinner('loading-spinner-discogs', 'Fetching folder contents');
  fetch(`http://127.0.0.1:5000/get_collection?folder=${folder}`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      hideSpinner('loading-spinner-discogs');
      displayCollection(data); // Update the UI with the data
    })
    .catch((error) => {
      console.error('Fetch error:', error.message);
    });
}

function transferCollectionToSpotify() {
  console.log(`Transfering to Spotify`);
  const feedbackElement = document.getElementById('feedback');
  showSpinner('loading-spinner-spotify', 'Searching Spotify');
  toggleTransferButton();
  fetch(`http://127.0.0.1:5000/transfer_to_spotify`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      // Enable and/or focus input element
      const listSpotify = document.getElementById('list-spotify'); //Check if there is already a playlist loaded to avoid disabling input
      const hasListItems = listSpotify.children.length > 0;

      if (!hasListItems) {
        togglePlaylistNameInput();
      }

      focusPlaylistNameInput();

      hideSpinner('loading-spinner-spotify');
      // Update the UI with the data
      displayPlaylist(data);
      toggleTransferButton();
    })
    .catch((error) => {
      toggleTransferButton();
      console.error('Fetch error:', error.message);
      hideSpinner('loading-spinner-spotify');
      feedbackElement.innerText = 'Error: Spotify - Log in first.';
    });
}

async function openAuthorizationUrl() {
  const response = await fetch('/authorize_discogs', { method: 'POST' });
  const data = await response.json();
  const authUrl = data.authorize_url;

  // Specify dimensions and features for the modal window
  const width = 800;
  const height = 600;
  const left = (window.outerWidth - width) / 2 + window.screenX;
  const top = (window.outerHeight - height) / 2 + window.screenY;

  const features = `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`;

  window.open(authUrl, 'authWindow', features); // Open the URL in a new tab or window
}

// Clear user tokens and enable login button
function logoutUser() {
  fetch('/logout')
    .then((response) => {
      if (response.ok) {
        disableLogoutButton();
        console.log('User logged out');
        checkSpotifyAuthorizationStatus();
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

// ---- SPOTIFY ----

function getSpotifyAuthURLAndRedirect() {
  fetch('/spotify_auth_url')
    .then((response) => response.json())
    .then((data) => {
      const authUrl = data.auth_url;
      // Open the URL in a new window
      const width = 800;
      const height = 600;
      const left = (window.outerWidth - width) / 2 + window.screenX;
      const top = (window.outerHeight - height) / 2 + window.screenY;

      const features = `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`;
      window.open(authUrl, 'SpotifyLoginWindow', features);

      // Poll to check if the window is closed
      const pollTimer = window.setInterval(function () {
        if (spotifyLoginWindow.closed !== false) {
          window.clearInterval(pollTimer);
          checkSpotifyAuthorizationAndUpdateButton(); // Check authorization status after login window is closed
        }
      }, 200);
    })
    .catch((error) => console.error('Error fetching Spotify auth URL:', error));
}

function createPlaylist() {
  playlistName = document.getElementById('playlist-name').value;
  const feedbackElement = document.getElementById('feedback');

  // Check if the playlistName is empty
  if (!playlistName.trim()) {
    // Update the UI to show an error message
    feedbackElement.innerText = 'Please enter a playlist name.';
    return;
  }

  togglePlaylistNameInput();
  toggleCreatePlaylistButton();

  feedbackElement.innerText = '';
  showSpinner('loading-spinner-spotify', 'Creating your playlist');
  fetch('/create_playlist', {
    method: 'POST', // Specify the method
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: playlistName,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      hideSpinner('loading-spinner-spotify');

      if (data.status === 'success') {
        console.log(data.message);
        feedbackElement.innerText = data.message;

        // Display the playlist URL or redirect the user
        const playlistLinkElement = document.createElement('a');
        playlistLinkElement.href = data.url;
        playlistLinkElement.innerText = 'Open in Spotify';
        playlistLinkElement.target = '_blank';
        feedbackElement.appendChild(playlistLinkElement);
        toggleSaveReportButton();
        togglePlaylistNameInput();
        toggleCreatePlaylistButton();
      } else {
        console.error(data.message);
        feedbackElement.innerText = data.message;
        togglePlaylistNameInput();
        toggleCreatePlaylistButton();
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      // Update the UI to show error
    });
}

// ---- OTHER ----

function seeReport() {
  fetch('/see_report')
    .then((response) => {
      if (!response.ok) {
        if (response.status === 404) {
          // Handle file not found specifically
          alert(
            'The report file has not been found. It is possible that the playlist has not been created yet.'
          );
        } else {
          // Handle other types of errors
          throw new Error('Network response was not ok.');
        }
        return; // Stop processing further since there was an error
      }
      // Assume the response is a blob
      return response.blob();
    })
    .then((blob) => {
      // Create a new object URL for the blob
      const url = window.URL.createObjectURL(blob);

      // Create a temporary anchor (link) element
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      // Provide a default name for the file to be downloaded
      a.download = 'export_report.txt';

      // Append the anchor to the body, click it, and then remove it
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    })
    .catch((error) => console.error('Error downloading report:', error));
}

// Function to check Spotify authorization status
function checkSpotifyAuthorizationStatus() {
  fetch('/check_spotify_authorization')
    .then((response) => response.json())
    .then((data) => {
      if (data.authorized) {
        toggleSpotifyLoginButton(data.authorized);
        enableLogoutButton();
      } else {
        disableLogoutButton();
      }
    })
    .catch((error) =>
      console.error('Error checking Spotify auth status:', error)
    );
}

// Function to toggle the Spotify login button based on authorization status
function toggleSpotifyLoginButton(isAuthorized) {
  const spotifyLoginButton = document.getElementById('spotifyLoginButton');
  if (isAuthorized) {
    spotifyLoginButton.disabled = true; // Disable the button if already authorized
    spotifyLoginButton.innerText = 'Spotify Authorized'; // Optional: Update the button text
  } else {
    spotifyLoginButton.disabled = false;
    spotifyLoginButton.innerText = 'Login with Spotify'; // Reset button text if needed
  }
}

document.addEventListener('DOMContentLoaded', () => {
  checkSpotifyAuthorizationStatus();
});

// ---- ELEMENT TOGGLE AND FOCUS----

function showSpinner(spinnerId, message) {
  const spinnerContainer = document.getElementById(spinnerId);
  if (spinnerContainer) {
    const spinnerText = spinnerContainer.querySelector('.spinner-text');
    spinnerText.innerText = message; // Set the action text
    spinnerContainer.style.display = 'flex';
  }
}

function hideSpinner(spinnerId) {
  const spinner = document.getElementById(spinnerId);
  if (spinner) spinner.style.display = 'none';
}

function togglePlaylistNameInput() {
  const inputField = document.getElementById('playlist-name');
  inputField.disabled = !inputField.disabled;
}

function focusPlaylistNameInput() {
  const inputField = document.getElementById('playlist-name');
  inputField.focus();
}

function toggleCreatePlaylistButtonOnInput() {
  // Check if the input is not empty to enable the button, else disable it
  const playlistName = document.getElementById('playlist-name').value;
  const button = document.getElementById('create-playlist-button');
  button.disabled = !playlistName.trim(); // Disable button if input is empty or only whitespace
}

function toggleCreatePlaylistButton() {
  // Check if the input is not empty to enable the button, else disable it
  const button = document.getElementById('create-playlist-button');
  button.disabled = !button.disabled;
}

function toggleReturnButton(showButton) {
  const button = document.getElementById('libraryReturnButton');
  button.disabled = !button.disabled;
  toggleTransferButton();
}

function toggleTransferButton(showButton) {
  const button = document.getElementById('libraryTransferButton');
  button.disabled = !button.disabled;
}

function toggleSaveReportButton(showButton) {
  const button = document.getElementById('seeReportButton');
  button.disabled = !button.disabled;
}

function disableLogoutButton(showButton) {
  const button = document.getElementById('logoutButton');
  button.disabled = true;
}

function enableLogoutButton(showButton) {
  const button = document.getElementById('logoutButton');
  button.disabled = false;
}