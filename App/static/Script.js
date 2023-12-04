function getCollection() {
  fetch('http://127.0.0.1:5000/get_collection')
    .then((response) => response.json())
    .then((data) => {
      // Update the UI with the data
      const albumList = document.getElementById('album-list');
      albumList.innerHTML = ''; // Clear previous data

      data.forEach((album) => {
        const listItem = document.createElement('li');
        listItem.textContent = `${album.artist} - ${album.title}`;
        albumList.appendChild(listItem);
      });
    });
}
