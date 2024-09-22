document.addEventListener('DOMContentLoaded', function() {

    const dateInput = document.getElementById("date-by");

    if (dateInput){
        const today = new Date();
        const nextYear = new Date(today);
        nextYear.setFullYear(today.getFullYear() + 1);
        
        const maxDate = new Date(today);
        maxDate.setFullYear(today.getFullYear() + 5);
    
        // Set minimum date to today
        dateInput.min = today.toISOString().split('T')[0];
    
        // Set maximum date to 5 years from today
        dateInput.max = maxDate.toISOString().split('T')[0];
    
        // Set default value to next year
        dateInput.value = nextYear.toISOString().split('T')[0];
    }



  //Carousel main page netflix style
      // Select all scroll containers and arrow controls
      const scrollContainers = document.querySelectorAll('.scroll-container');
      const leftArrows = document.querySelectorAll('.arrow-left');
      const rightArrows = document.querySelectorAll('.arrow-right');

      // Bigger arrows on hover
        leftArrows.forEach((arrowDiv, index) => {
          const arrowIcon = arrowDiv.querySelector('.arrow-icon');

          arrowDiv.addEventListener('mouseenter', () => {
            arrowIcon.setAttribute('width', '32');
            arrowIcon.setAttribute('height', '32');
          });

          arrowDiv.addEventListener('mouseleave', () => {
            arrowIcon.setAttribute('width', '28');
            arrowIcon.setAttribute('height', '28');
          });
      });

      rightArrows.forEach((arrowDiv, index) => {
        const arrowIcon = arrowDiv.querySelector('.arrow-icon');

        arrowDiv.addEventListener('mouseenter', () => {
          arrowIcon.setAttribute('width', '32');
          arrowIcon.setAttribute('height', '32');
        });

        arrowDiv.addEventListener('mouseleave', () => {
          arrowIcon.setAttribute('width', '28');
          arrowIcon.setAttribute('height', '28');
        });
    });
  
      // Add event listeners to each pair of arrows for each scroll container
      scrollContainers.forEach((scrollContainer, index) => {
          const leftArrow = leftArrows[index];
          const rightArrow = rightArrows[index];
  
          // Hide the left arrow initially if at the beginning
          if (scrollContainer.scrollLeft === 0) {
              leftArrow.style.display = 'none';
          }
  
          // Hide the right arrow initially if at the end
          if (scrollContainer.scrollLeft + scrollContainer.clientWidth >= scrollContainer.scrollWidth) {
              rightArrow.style.display = 'none';
          }
  
          // Function to scroll left by one visible space
          leftArrow.addEventListener('click', function(event) {
              event.preventDefault();
              scrollContainer.scrollTo({
                  left: scrollContainer.scrollLeft - scrollContainer.clientWidth,
                  behavior: 'smooth'
              });
          });
  
          // Function to scroll right by one visible space
          rightArrow.addEventListener('click', function(event) {
              event.preventDefault();
              scrollContainer.scrollTo({
                  left: scrollContainer.scrollLeft + scrollContainer.clientWidth,
                  behavior: 'smooth'
              });
          });
  
          // Update arrow visibility on scroll
          scrollContainer.addEventListener('scroll', function() {
              // Check if scroll position is at the beginning
              if (scrollContainer.scrollLeft === 0) {
                  leftArrow.style.display = 'none';
              } else {
                  leftArrow.style.display = 'block';
              }
  
              // Check if scroll position is at the end
              if (scrollContainer.scrollLeft + scrollContainer.clientWidth >= scrollContainer.scrollWidth) {
                  rightArrow.style.display = 'none';
              } else {
                  rightArrow.style.display = 'block';
              }
          });
      });



  // Main Carrousel
  let slides;

  if (typeof staticUrls !== 'undefined') {
      slides = [
          {
              title: 'Access Raw Material prices and forecasts for <span class="text-blue-600 dark:text-blue-500">10,000+</span> products',
              text: 'Manufactured in the UK and all over the world',
              img: staticUrls.image1
          },
          {
              title: 'Analyse any custom product risk <span class="text-blue-600 dark:text-blue-500">easier, faster, cheaper</span>',
              text: 'Never be surprised of upcoming price increase and negotiate price decrease sooner',
              img: staticUrls.image2
          },
          {
              title: 'Understand forecasts with no experience in <span class="text-blue-600 dark:text-blue-500">Commodity Trading</span>',
              text: "You do not need Master's in Finance to know what forces impact market and what are the current odds",
              img: staticUrls.image3
          },
          {
              title: 'Know more than manufacturers and use the <span class="text-blue-600 dark:text-blue-500">information advantage</span>',
              text: 'Analyse products and commodities sooner than anyone average',
              img: staticUrls.image4
          }
      ];


      let currentSlide = 0;
  const totalSlides = slides.length;
  const slideInterval = 5000;
  const carouselDots = document.querySelectorAll('.carousel-dot');
  const carouselTitle = document.querySelector('.carousel-title');
  const carouselText = document.querySelector('.carousel-text');
  const carouselImage = document.querySelector('.carousel-image img');
  const carouselContent = document.querySelector('.carousel-content');

  function updateSlide(index) {
    const slide = slides[index];

    // Fade out
    carouselImage.classList.remove('active');
    carouselContent.classList.remove('active');

    setTimeout(() => {
      // Update content
      carouselTitle.innerHTML = slide.title;
      carouselText.textContent = slide.text;
      carouselImage.src = slide.img;

      // Fade in
      carouselImage.classList.add('active');
      carouselContent.classList.add('active');

      // Update dots
      carouselDots.forEach(dot => {
        dot.classList.remove('bg-blue-500');
        dot.classList.add('bg-gray-300');
      });
      carouselDots[index].classList.remove('bg-gray-300');
      carouselDots[index].classList.add('bg-blue-500');
    }, 500); // Match the timeout duration to CSS transition duration
  }

  function nextSlide() {
    currentSlide = (currentSlide + 1) % totalSlides;
    updateSlide(currentSlide);
  }

  let slideTimer = setInterval(nextSlide, slideInterval);

  carouselDots.forEach(dot => {
    dot.addEventListener('click', function () {
      clearInterval(slideTimer);
      currentSlide = parseInt(this.dataset.index);
      updateSlide(currentSlide);
      slideTimer = setInterval(nextSlide, slideInterval);
    });
  });

  updateSlide(currentSlide);
  }
    
  


  // Pricing logic, form submission
  const monthlyBtn = document.getElementById('monthly-btn');
  const yearlyBtn = document.getElementById('yearly-btn');
  const yearlyDivs = document.getElementsByClassName('yearly-plan');
  const monthlyDivs = document.getElementsByClassName('monthly-plan');
  

  if (monthlyBtn) {
  monthlyBtn.addEventListener('click', function() {
      monthlyBtn.classList.remove('bg-transparent', 'text-gray-800', 'dark:text-gray-200', 'dark:hover:bg-gray-800', 'hover:bg-gray-200');
      monthlyBtn.classList.add('bg-blue-500', 'text-white');

      yearlyBtn.classList.remove('bg-blue-500', 'text-white');
      yearlyBtn.classList.add('bg-transparent', 'text-gray-800', 'dark:text-gray-200', 'dark:hover:bg-gray-800', 'hover:bg-gray-200');
      
      // Show monthly divs and hide yearly divs
      for (let div of monthlyDivs) {
          div.style.display = 'block';
      }
      for (let div of yearlyDivs) {
          div.style.display = 'none';
      }
  
    });

  yearlyBtn.addEventListener('click', function() {
      yearlyBtn.classList.remove('bg-transparent', 'text-gray-800', 'dark:text-gray-200', 'dark:hover:bg-gray-800', 'hover:bg-gray-200');
      yearlyBtn.classList.add('bg-blue-500', 'text-white');
      monthlyBtn.classList.remove('bg-blue-500', 'text-white');
      monthlyBtn.classList.add('bg-transparent', 'text-gray-800', 'dark:text-gray-200', 'dark:hover:bg-gray-800', 'hover:bg-gray-200');

      // Show yearly divs and hide monthly divs
      for (let div of yearlyDivs) {
          div.style.display = 'block';
      }
      for (let div of monthlyDivs) {
          div.style.display = 'none';
      }
    });

  document.querySelectorAll('.choose-plan').forEach(button => {
      button.addEventListener('click', function() {
          const plan = this.getAttribute('data-plan');
          console.log(`Chosen plan: ${plan}`);
          // Handle plan selection logic here (e.g., form submission)
      });
  });
  }



  // For Create.html

const addButton = document.querySelector('#add-row');
const rowsContainer = document.querySelector('#rows-container');

// Function to create a new row
function createNewRow(rowCount) {
    const newRowId = `row-${rowCount}`;

    // Create a new row container
    const newRow = document.createElement('div');
    newRow.id = newRowId;
    newRow.className = 'flex flex-row items-center';

    // Delete button
    const deleteButton = document.createElement('a');
    deleteButton.href = '#';
    deleteButton.className = 'delete-row mr-2';
    deleteButton.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="16" fill="#FF0000"></circle>
            <path d="M9.26318 16H22.7369" stroke="#E9E9E9" stroke-width="3" stroke-linecap="round"></path>
            <path d="M9.26318 16H22.7369" stroke="#E9E9E9" stroke-width="3" stroke-linecap="round"></path>
            <path d="M9.26318 16H22.7369" stroke="#E9E9E9" stroke-width="3" stroke-linecap="round"></path>
        </svg>
    `;
    deleteButton.addEventListener('click', function() {
        rowsContainer.removeChild(newRow); // Remove current row
    });

    // Input for content name
    const contentInput = document.createElement('input');
    contentInput.type = 'text';
    contentInput.name = `content-name-${rowCount}`;
    contentInput.className = 'rounded-l-lg block mt-2 w-full placeholder-gray-400/70 dark:placeholder-gray-500 border border-gray-200 bg-white px-2.5 py-2.5 text-gray-700 focus:border-blue-400 focus:outline-none focus:ring focus:ring-blue-300 focus:ring-opacity-40 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300 dark:focus:border-blue-300';
    contentInput.placeholder = 'Content ' + rowCount;
    contentInput.required = true;

    // Select for commodities
    const commoditiesSelect = document.createElement('select');
    commoditiesSelect.className = 'block mt-2 w-full placeholder-gray-400/70 dark:placeholder-gray-500 border border-gray-200 bg-white px-2.5 py-2.5 text-gray-700 focus:border-blue-400 focus:outline-none focus:ring focus:ring-blue-300 focus:ring-opacity-40 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300 dark:focus:border-blue-300';
    commoditiesSelect.name = `content-commodity-${rowCount}`;
    commoditiesSelect.required = true;

    const optionDefault = document.createElement('option');
    optionDefault.value = '';
    optionDefault.textContent = 'Select Commodity';
    optionDefault.disabled = true;
    optionDefault.selected = true;
    optionDefault.hidden = true;
    commoditiesSelect.appendChild(optionDefault);

    commodities.forEach(commodity => {
        const option = document.createElement('option');
        option.value = commodity.commodity_id;
        option.textContent = commodity.commodity_name;
        commoditiesSelect.appendChild(option);
    });

    // Input for number
    const numberInput = document.createElement('input');
    numberInput.type = 'number';
    numberInput.name = `content-proportion-${rowCount}`;
    numberInput.className = 'lg:w-20 w-14 block mt-2 placeholder-gray-400/70 dark:placeholder-gray-500 rounded-r-lg border border-gray-200 bg-white px-2.5 py-2.5 text-gray-700 focus:border-blue-400 focus:outline-none focus:ring focus:ring-blue-300 focus:ring-opacity-40 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300 dark:focus:border-blue-300 col-span-1';
    numberInput.placeholder = '25';
    numberInput.min = '0';
    numberInput.step = 'any';
    numberInput.required = true;

    // Append elements to the row container
    newRow.appendChild(deleteButton);
    newRow.appendChild(contentInput);
    newRow.appendChild(commoditiesSelect);
    newRow.appendChild(numberInput);

    // Append the new row to the rows container
    rowsContainer.appendChild(newRow);
}

const saveButton = document.getElementById('save-button'); // Assuming your button has this id


if (saveButton) {

// Function to update the save button state
function updateSaveButtonState() {
    if (rowsContainer.children.length === 0) {
        // Alternatively, you can disable the button
        // saveButton.disabled = true;
       
        saveButton.style.display = 'none';
    } else {
        // Enable the button if disabled
        // saveButton.disabled = false;
        
        saveButton.style.display = 'block';
    }
}

// Event listener for adding new rows
addButton.addEventListener('click', function(e) {
    e.preventDefault();
    const rowCount = rowsContainer.children.length + 1;
    createNewRow(rowCount);
    updateSaveButtonState(); // Update the button state after adding a new row
});

// Event delegation for delete row buttons
document.getElementById('rows-container').addEventListener('click', function(event) {
    if (event.target.closest('.delete-row')) {
        const row = event.target.closest('.flex-row');
        row.remove(); // Remove the row
        updateSaveButtonState(); // Update the button state after removing a row
    }
});

updateSaveButtonState();
}




  // Function to get query parameters from the URL
  function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
  }

  // Get the current 'pagec' value from the URL
  const currentPagec = getQueryParam('pagec');

  // Get the previous 'pagec' value from localStorage
  const previousPagec = localStorage.getItem('previousPagec');

  // Only scroll to the header if the 'pagec' value has changed
  if (currentPagec !== previousPagec && currentPagec !== null) {
    // Scroll to the element with id 'commodities-header'
    document.getElementById("commodities-header").scrollIntoView({ behavior: 'smooth' });
  }

  // Update localStorage with the current 'pagec' value for future checks
  localStorage.setItem('previousPagec', currentPagec);



});