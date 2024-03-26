// ---- DISCOGS ----

// function to initiate connection to Discogs by authorising user and then fetching authorised user library
async function startImportProcess() {
  const response = await fetch('/check_authorization'); // check if user is already authorised
  const { authorized } = await response.json();

  if (authorized) {
    // if authorised proceed with fetching library data
    enableLogoutButton();
    getLibrary();
  } else {
    // if not authorised proceed with authorisation
    await openAuthorizationUrl();
    checkAuthorizationStatus(); // Start polling for authorization status
  }
}

// Open modal authorization winwdow for Discogs
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

  window.open(authUrl, 'authWindow', features);
}

function checkAuthorizationStatus() {
  // Polling every 5 seconds to check if authorization is complete
  const interval = setInterval(async () => {
    const response = await fetch('/check_authorization');
    const { authorized } = await response.json();

    if (authorized) {
      enableLogoutButton();
      clearInterval(interval);
      getLibrary(); // Fetch the Discogs library
    }
  }, 5000);
}

// Navigate back to library view
function returnToLibrary() {
  disableReturnButton();
  disableTransferButton();
  getLibrary();
}

// Fetch user library folders data from Discogs
function getLibrary() {
  const feedbackElement = document.getElementById('feedback');
  feedbackElement.innerText = '';
  showSpinner('loading-spinner-discogs', 'Fetching your library');
  fetch(`${window.api_url}/get_library`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      hideSpinner('loading-spinner-discogs');
      const userInfo = document.querySelector('.user-info.discogs');
      userInfo.style.visibility = 'visible';
      userInfo.querySelector('a').textContent = data.user_info.username;
      userInfo.querySelector('a').href = data.user_info.url;
      displayLibrary(data.library); // Update the UI with the data
    })
    .catch((error) => {
      console.error('Fetch error:', error.message);
      hideSpinner('loading-spinner-discogs');
      feedbackElement.innerText =
        'Error: Discogs - There was an issue fetching your collection on the server side. Try again later.';
    });
}

// Fetch selected folder content data from Discogs
function getCollection(folder) {
  const feedbackElement = document.getElementById('feedback');
  feedbackElement.innerText = ''; // Clear previous data
  showSpinner('loading-spinner-discogs', 'Fetching folder contents');

  fetch(`${window.api_url}/get_collection?folder=${folder}`)
    .then((response) => {
      if (!response.ok) {
        // If server response is not ok, throw an error with the status
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      hideSpinner('loading-spinner-discogs');
      displayCollection(data); // Update UI with the data
    })
    .catch((error) => {
      console.error('Fetch error:', error.message);
      hideSpinner('loading-spinner-discogs');
      feedbackElement.innerText =
        'Error: Discogs - There was an issue fetching your collection on the server side. Try again later.';
    });
}

// Present fetched Discogs library to the user
function displayLibrary(data) {
  const libraryList = document.getElementById('list-discogs');
  libraryList.innerHTML = ''; // Clear previous data
  const template = document.getElementById('folderTemplate');

  data.forEach((folder, index) => {
    const clone = document.importNode(template.content, true);

    clone.querySelector('.folder-index').textContent = `${index + 1}`;
    clone.querySelector('.folder-name').textContent = folder.folder;
    clone.querySelector('.folder-count').textContent = folder.count;

    // Set the ID on the <li> for reference
    const listItem = clone.querySelector('li');
    listItem.id = `folder-${index}`;

    // Add click event listener to library folder
    listItem.addEventListener('click', () => getCollection(index));

    libraryList.appendChild(clone);
  });
}

// Present contents of selected Discogs library folder to the user
function displayCollection(data) {
  const albumList = document.getElementById('list-discogs');
  albumList.innerHTML = ''; // Clear previous data
  const template = document.getElementById('albumTemplate');

  data.forEach((album, index) => {
    const clone = document.importNode(template.content, true);

    clone.querySelector('.album-index').textContent = `${index + 1}`;
    clone.querySelector('.album-artist').textContent = album.artist;
    clone.querySelector('.album-title').textContent = album.title;
    clone.querySelector('.album-cover').setAttribute('src', album.cover);

    // Set the ID on the <li> for reference
    const listItem = clone.querySelector('li');
    listItem.id = `${album.discogs_id}`;

    albumList.appendChild(clone);
  });

  enableReturnButton();
  enableTransferButton();
}

// remove potentially
window.addEventListener(
  'message',
  (event) => {
    if (event.data === 'authorizationComplete') {
      // Close modal if you have one open
      // Refresh data or UI as necessary
    }
  },
  false
);

// ---- SPOTIFY ----

// Open modal authorization winwdow for Spotify
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
      const spotifyAuthWindow = window.open(
        authUrl,
        'SpotifyLoginWindow',
        features
      );

      // Poll to check if the window is closed
      const pollTimer = window.setInterval(function () {
        if (spotifyAuthWindow.closed !== false) {
          window.clearInterval(pollTimer);
          checkSpotifyAuthorizationStatus(); // Check authorization status after login window is closed
        }
      }, 200);
    })
    .catch((error) => console.error('Error fetching Spotify auth URL:', error));
}

// Looking up Discogs collection items in Spotify catalog
function transferCollectionToSpotify() {
  const feedbackElement = document.getElementById('feedback');
  feedbackElement.innerText = '';
  showSpinner('loading-spinner-spotify', 'Searching Spotify');
  disableTransferButton();

  fetch(`${window.api_url}/transfer_to_spotify`)
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
        feedbackElement.innerText =
          'Discogs folder contents were converted to Spotify list successfully. You can see any albums that could not be found highlighted in red in the Discogs window. ';
      }

      focusPlaylistNameInput();

      hideSpinner('loading-spinner-spotify');
      displayPlaylist(data); // Update UI with the data
      enableTransferButton();
    })
    .catch((error) => {
      disableTransferButton();
      console.error('Fetch error:', error.message);
      hideSpinner('loading-spinner-spotify');
      feedbackElement.innerText = 'Error: Spotify - Log in first.';
    });
}

// Create Spotify playlist
function createPlaylist() {
  playlistName = document.getElementById('playlist-name').value;
  const feedbackElement = document.getElementById('feedback');
  feedbackElement.innerText = ''; // Clear previous data

  // Handle case if playlistName is empty
  if (!playlistName.trim()) {
    feedbackElement.innerText = 'Please enter a playlist name.';
    return;
  }

  togglePlaylistNameInput();
  toggleCreatePlaylistButton();
  showSpinner('loading-spinner-spotify', 'Creating your playlist');

  // create playlist
  fetch('/create_playlist', {
    method: 'POST',
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

      // Display feedback and link to the playlist
      if (data.status === 'success') {
        feedbackElement.innerText = data.message;
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
    });
}

// Present the results of searching collection contents on Spotify to the user
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

      // Communicate items that were not found in Spotify catalog by highlighting respective items in the Discogs field
      if (albumElementInLibrary) {
        albumElementInLibrary.classList.add('not-found-highlight');
      }
    }
  });
}

// ---- OTHER ----

// Clear user tokens, UI data and enable login button
function logoutUser() {
  fetch('/logout')
    .then((response) => {
      if (response.ok) {
        disableLogoutButton();
        disableReturnButton();
        disableTransferButton();
        disableCreatePlaylistButton();
        disablePlaylistNameInput();
        checkSpotifyAuthorizationStatus();

        // Clear discogs user info
        const userInfo = document.querySelector('.user-info');
        userInfo.querySelector('a').textContent = '';
        userInfo.querySelector('a').href = '';
        userInfo.style.visibility = 'hidden';

        // Clear library and playlist list
        clearLibraryAndPlaylistLists();

        // Clear playlist name input
        const inputField = document.getElementById('playlist-name');
        inputField.value = '';
      }
    })
    .catch((error) => console.error('Error logging out:', error));
}

// Clear data from Discogs and Spotify list windows
function clearLibraryAndPlaylistLists() {
  const libraryList = document.getElementById('list-discogs');
  const playlistList = document.getElementById('list-spotify');
  const feedbackElement = document.getElementById('feedback');

  libraryList.innerHTML = '';
  playlistList.innerHTML = '';
  feedbackElement.innerText = '';
}

function seeReport() {
  fetch('/see_report')
    .then((response) => {
      if (!response.ok) {
        if (response.status === 404) {
          // Handle file not found
          alert(
            'The report file has not been found. It is possible that the playlist has not been created yet.'
          );
        } else {
          // Handle other types of errors
          throw new Error('Network response was not ok.');
        }
        return;
      }
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
      toggleSpotifyLoginButton(data.authorized);
      const userInfo = document.querySelector('.user-info.spotify');
      if (data.authorized) {
        userInfo.querySelector('a').innerText = data.username;
        userInfo.querySelector('a').href = data.url;
        userInfo.style.visibility = 'visible';

        if (document.getElementById('libraryReturnButton').disabled != true) {
          enableTransferButton();
        }

        enableLogoutButton();
      } else {
        disableLogoutButton();
        userInfo.querySelector('a').innerText = '';
        userInfo.querySelector('a').href = '';
        userInfo.style.visibility = 'hidden';
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
  } else {
    spotifyLoginButton.disabled = false;
  }
}

// Document Event Listeners

document.addEventListener('DOMContentLoaded', () => {
  checkSpotifyAuthorizationStatus;
});

document
  .getElementById('discogsImportButton')
  .addEventListener('click', startImportProcess);

document
  .getElementById('spotifyLoginButton')
  .addEventListener('click', getSpotifyAuthURLAndRedirect);

document.getElementById('seeReportButton').addEventListener('click', seeReport);

document.getElementById('logoutButton').addEventListener('click', logoutUser);

document
  .getElementById('libraryReturnButton')
  .addEventListener('click', returnToLibrary);

document
  .getElementById('libraryTransferButton')
  .addEventListener('click', transferCollectionToSpotify);

document
  .getElementById('create-playlist-button')
  .addEventListener('click', createPlaylist);

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

function disablePlaylistNameInput() {
  const inputField = document.getElementById('playlist-name');
  inputField.disabled = true;
}

function focusPlaylistNameInput() {
  const inputField = document.getElementById('playlist-name');
  inputField.focus();
}

function toggleCreatePlaylistButtonOnInput() {
  const playlistName = document.getElementById('playlist-name').value;
  const button = document.getElementById('create-playlist-button');
  button.disabled = !playlistName.trim(); // Disable button if input is empty or only whitespace
}

function disableCreatePlaylistButton() {
  const button = document.getElementById('create-playlist-button');
  button.disabled = true;
}

function toggleCreatePlaylistButton() {
  const button = document.getElementById('create-playlist-button');
  button.disabled = true;
}

function enableReturnButton() {
  const button = document.getElementById('libraryReturnButton');
  button.disabled = false;
}

function disableReturnButton() {
  const button = document.getElementById('libraryReturnButton');
  button.disabled = true;
}

function toggleSaveReportButton() {
  const button = document.getElementById('seeReportButton');
  button.disabled = !button.disabled;
}

function enableTransferButton() {
  const spotifyLoginButton = document.getElementById('spotifyLoginButton');
  const button = document.getElementById('libraryTransferButton');
  if (spotifyLoginButton.disabled == true) {
    //enable the button only if user has logged into Spotify
    button.disabled = false;
  }
}

function disableTransferButton() {
  const button = document.getElementById('libraryTransferButton');
  button.disabled = true;
}

function enableLogoutButton() {
  const button = document.getElementById('logoutButton');
  button.disabled = false;
}

function disableLogoutButton() {
  const button = document.getElementById('logoutButton');
  button.disabled = true;
}
