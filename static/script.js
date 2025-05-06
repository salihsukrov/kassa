var body = $("#body");
var loader = $("#loader")
var root = $("#root");
var select = $("#select")
var payment = $("#payment")
var pcl = $("#pcl");



async function toggle_loader() {

  if (loader.hasClass("hidden")) {
    loader.removeClass('hidden')
    pcl.addClass('hidden')
  }
  else {
    loader.addClass('hidden')
    pcl.removeClass('hidden')
  }

}

$("#pay-qiwi").on("click", async function (e) {
  await toggle_loader();
  fetch('localhost:8080/api/setMethod?uuid=uuid&method_id=1')
    .then(resp => {
      alert(resp.text())
      success_toast('Выбран способ оплаты QIWI')
      setTimeout(() => {
        location.reload()
      }, 500);
    }).catch(err => {
      error_toast('Ошибка при работе с API')
    })
})

async function error_toast(text) {
  Toastify({
    text: text,
    duration: 3000,
    newWindow: true,
    gravity: "top", // `top` or `bottom`
    position: "right", // `left`, `center` or `right`
    stopOnFocus: true, // Prevents dismissing of toast on hover
    style: {
      background: "linear-gradient(to right, #fc3503, #f0451a)",
    },
    onClick: function () { } // Callback after click
  }).showToast();
}

async function success_toast(text) {
  Toastify({
    text: text,
    duration: 3000,
    newWindow: true,
    gravity: "top", // `top` or `bottom`
    position: "right", // `left`, `center` or `right`
    stopOnFocus: true, // Prevents dismissing of toast on hover
    style: {
      background: "linear-gradient(to right, #1CA93A, #00CC2C)",
    },
    onClick: function () { } // Callback after click
  }).showToast();
}

function copy(text) {
  navigator.clipboard.writeText(`${text}`)
  success_toast('Текст успешно скопирован!')
}


