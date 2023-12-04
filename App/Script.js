function getCollection() {
  fetch("/get_collection")
    .then((response) => response.json())
    .then((data) => {
      // Update the UI with the data
      const albumList = document.getElementById("album-list");
      albumList.innerHTML = ""; // Clear previous data

      data.forEach((album) => {
        const listItem = document.createElement("li");
        listItem.textContent = `${album.artist} - ${album.title}`;
        albumList.appendChild(listItem);
      });
    });
}
