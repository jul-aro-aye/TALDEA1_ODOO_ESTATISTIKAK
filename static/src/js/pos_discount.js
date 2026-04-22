odoo.define('jatetxeko_estatistikak.pos_discount', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    const JatetxekoPaymentScreen = PaymentScreen => class extends PaymentScreen {
        async click_deskontu_kodea() {
            const { confirmed, payload } = await this.showPopup('TextInputPopup', {
                title: 'Deskontu Kodea',
                startingValue: '',
            });

            if (confirmed) {
                const kodea = payload;
                try {
                    const emaitza = await this.rpc({
                        route: '/jatetxeko/egiaztatu_deskontua',
                        params: { kodea: kodea },
                    });

                    if (emaitza.existitzen_da) {
                        const order = this.currentOrder;
                        const deskontu_balioa = emaitza.balioa;
                        
                        order.get_orderlines().forEach(line => {
                            line.set_discount(deskontu_balioa);
                        });
                        
                        this.showPopup('ConfirmPopup', {
                            title: 'Ondo!',
                            body: 'Deskontua aplikatu da: ' + deskontu_balioa + '%',
                        });
                    } else {
                        this.showPopup('ErrorPopup', {
                            title: 'Errorea',
                            body: 'Kodea ez da existitzen edo ez dago aktibo.',
                        });
                    }
                } catch (error) {
                    this.showPopup('ErrorPopup', {
                        title: 'Errorea',
                        body: 'Ezin izan da API-arekin konektatu.',
                    });
                }
            }
        }
    };

    Registries.Component.extend(PaymentScreen, JatetxekoPaymentScreen);

    return PaymentScreen;
});
