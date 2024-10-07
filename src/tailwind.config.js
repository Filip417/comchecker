module.exports = {
  content: [
      './main/templates/**/*.html'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

// command to create new output.css: npx tailwindcss -i ./static/src/input.css -o ./static/src/output.css --watch
// then manually upload output.css for now or include 