define( movea,`load RA $2' )
define( sprite,`.data eval(($1 * 4) + ($2 * 2) + $3)' )
define( space ,`forloop(`i',0,`$1',`.data 0')' )
