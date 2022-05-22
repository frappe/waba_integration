// Copyright (c) 2022, Hussain Nagaria and contributors
// For license information, please see license.txt

frappe.ui.form.on("WABA WhatsApp Message", {
  refresh: function (frm) {
    const btn = frm.add_custom_button("Send Message", () => {
      frm
        .call({
          doc: frm.doc,
          method: "send",
          btn,
        })
        .then((m) => frm.refresh());
    });
  },
});
