// Basic JavaScript to toggle mobile navigation
document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');

  navToggle.addEventListener('click', () => {
    const isExpanded = mainNav.style.display === 'block';
    mainNav.style.display = isExpanded ? 'none' : 'block';
    navToggle.querySelector('i').classList.toggle('fa-bars');
    navToggle.querySelector('i').classList.toggle('fa-times');
  });
});