const nameConfig = JSON.parse(document.getElementById('name-config').textContent);
let directChanged = false
let orderChanged = false

const nameField = document.querySelector("#id_member__name")

if (nameField) {
  const orderField = document.querySelector("#id_member__order_name")
  const directField = document.querySelector("#id_member__direct_address_name")

  orderField.addEventListener("input", (ev) => orderChanged = true)
  directField.addEventListener("input", (ev) => directChanged = true)

  nameField.addEventListener("input", (ev) => {
    if (nameField.value) {
      const nameParts = nameField.value.trim().split(" ")
      const first = nameParts[0]
      const last = nameParts[nameParts.length - 1]
      if (!directChanged) {
        directField.value = nameConfig.direct === "first" ? first : last
      }
      if (!orderChanged) {
        orderField.value = nameConfig.order === "first" ? first : last
      }

    }
  })
}
