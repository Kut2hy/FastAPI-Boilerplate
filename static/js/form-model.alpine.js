document.addEventListener('alpine:init', () => {
    Alpine.data(
        "SimpleFormModel", () => ({
            isValid: false,
            formElement: null,

            init() {
                this.revalidate();
                this.formElement = this.$el;
            },

            revalidate() {
                this.isValid = this.$el.checkValidity();
            },

            // The native `reset` event fires BEFORE the browser clears the
            // fields, so we defer the validity check to the next tick.
            revalidateDeferred() {
                this.$nextTick(() => { this.revalidate(); });
            },

            // CSP build can't evaluate `!isValid` inline, expose a getter.
            get isDisabled() {
                return !this.isValid;
            },
        })
    );
});