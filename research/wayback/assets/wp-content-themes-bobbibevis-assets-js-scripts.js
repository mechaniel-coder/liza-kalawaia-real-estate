(function ($, w, d, h, b) {

    var app = {

        initNavigation: function () {
            var $nav = jQuery('.block-header__nav-list');
            if ($nav.length > 0) $nav.navTabDoubleTap();
        },
        initFeaturedProperties: function () {
            /* Put featured properties code here */

                              jQuery(".fp-slider").slick({
                                slidesToShow: 3,
                                slidesToScroll: 1,
                                autoplay: true,
                                autoplaySpeed: 6000,
                                arrows: true,
                                prevArrow:'.hpfp .sc-arrow-prev',
                                nextArrow:'.hpfp .sc-arrow-next',
                                responsive: [
                                  {
                                    breakpoint: 991,
                                    settings: {
                                      slidesToShow: 2,
                                    }
                                  },
                                  {
                                    breakpoint: 600,
                                    settings: {
                                      slidesToShow: 1,
                                    }
                                  }
                                ],
                              });


        },

        initsidenav: function(){

                  jQuery('.block-header__burger-menu , .block-slide-close-burger-menu').click(function(){

                        var burgermenu  = jQuery(this);
                        var slidemenu = jQuery('.block-slide-menu-content');
                        var sbody = jQuery('body');

                        if(jQuery(burgermenu).hasClass('active')){

                            burgermenu.removeClass('active');
                            slidemenu.removeClass('active');

                            jQuery('.block-slide-close-burger-menu').removeClass('active');
                            jQuery('.block-header__burger-menu').removeClass('active');
                            jQuery('.block-offcanvas-backdrop').hide();


                              //restore:
                                jQuery('html, body').css({
                                    overflow: 'initial',
                                    height: 'auto'
                                });

                        }else{

                            burgermenu.addClass('active');
                            slidemenu.addClass('active');
                            jQuery('.block-slide-close-burger-menu').addClass('active');
                            jQuery('.block-slide-close-burger-menu').addClass('active');
                            jQuery('.block-offcanvas-backdrop').show();

                              //disable scrolling:
                              jQuery('html, body').css({
                                  overflow: 'visible hidden',
                                  height: 'auto'
                              });


                        }

                });

              jQuery('.block-offcanvas-backdrop').click(function(){

                jQuery('.block-slide-close-burger-menu').removeClass('active');
                jQuery('.block-header__burger-menu').removeClass('active');
                jQuery('.block-offcanvas-backdrop').hide();
                jQuery('.block-slide-menu-content').removeClass('active');
                    jQuery('html, body').css({
                        overflow: 'initial',
                        height: 'auto'
                    });
              });











        },
        initMouseScrollDown: function () {



          function fixedHeader() {
              var headerHeight = jQuery('header.building-blocks__header--2-wolf').outerHeight() + 100;
              if (jQuery(document).scrollTop() > headerHeight) {
                  jQuery('header.building-blocks__header--2-wolf').addClass('show-fixed');
              }
              else {
                  jQuery('header.building-blocks__header--2-wolf').removeClass('show-fixed');
              }
          }


          jQuery(document).on('scroll orientationchange resize load', function () {
              fixedHeader();
          });


          fixedHeader();


        },
        initFeaturedCommunities: function () {
            /* Put featured communities code here */
        },
        initTestimonials: function () {
            /* Put testimonials code here */
        },
        initQuickSearch: function() {





          function addSeparator(nStr) {
        nStr += '';
        var x = nStr.split('.');
        var x1 = x[0];
        var x2 = x.length > 1 ? '.' + x[1] : '';
        var rgx = /(\d+)(\d{3})/;
        while (rgx.test(x1)) {
            x1 = x1.replace(rgx, '$1' + ',' + '$2');
        }
        return x1 + x2;
    }

    function rangeInputChangeEventHandler(e) {
        var minLabel = $(this).closest('.range-slider').find('span.min'),
            maxLabel = $(this).closest('.range-slider').find('span.max'),
            minInput = $(this).closest('.range-slider').find('input.min'),
            maxInput = $(this).closest('.range-slider').find('input.max'),
            minInputVal = parseInt($(minInput).val()),
            maxInputVal = parseInt($(maxInput).val()),
            origin = $(this).context.className;

        if (origin === 'min' && minInputVal > maxInputVal) {
            $(minInput).val(maxInputVal);
            minInputVal = parseInt($(minInput).val());
        }

        if (origin === 'max' && maxInputVal < minInputVal) {
            $(maxInput).val(minInputVal);
            maxInputVal = parseInt($(maxInput).val());
        }

        // Update minimum label
        if (minInputVal === 0) {
            $(minLabel).html('$0');
        } else {
            $(minLabel).html('$' + addSeparator(minInputVal));
        }

        // Update maximum label
        if (maxInputVal === 150000000) {
            $(maxLabel).html('$' + addSeparator(maxInputVal) + '+');
        } else {
            $(maxLabel).html('$' + addSeparator(maxInputVal));
        }
    }

    $('.range-slider input[type="range"]').on('input', rangeInputChangeEventHandler);






        },

        initCustomFunction: function () {
            /* See the pattern? Create more functions like this if needed. */



            if (jQuery('body').hasClass('home')) {
                function setPadding() {
                  var exactHeight = jQuery('.fp-item .fp-info')[0].getBoundingClientRect().height;

                  jQuery('.fp-item a').each(function() {
                      jQuery(this).css('padding-bottom', exactHeight + 'px');
                  });
                }

                setPadding();

                jQuery(window).resize(function() {
                  setPadding();
                });

                }


        }

    }


    jQuery(document).ready(function () {


    		AOS.init();

      app.initsidenav();
      app.initMouseScrollDown();

        /* Initialize navigation */
        app.initNavigation();

        /* Initialize featured properties */
        app.initFeaturedProperties();

        /* Initialize featured communities */
        app.initFeaturedCommunities();

        /* Initialize testimonials */
        app.initTestimonials();

        /* Initialize quick search */
        app.initQuickSearch();

        app.initCustomFunction();



    });

    jQuery(window).on('load', function () {


    })


})(jQuery, window, document, 'html', 'body');
