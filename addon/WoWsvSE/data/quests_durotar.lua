-- GENERATED FILE — do not edit by hand.
-- Swedish quest text for Durotar, keyed by quest ID.
--
-- Written by WoWsvSE emit 0.1.0
-- Game build: TBC Anniversary 2.5.6 (69110), Interface 20506
-- UI strings: Ketho/BlizzardInterfaceResources@d6d4a8f4
-- Quest data: Questie/Questie@4aea09ec + cmangos/tbc-db@da2de07e
--
-- To change anything here, fix the toolchain and run `make all`.
local _, SVSE = ...

-- Keyed by numeric quest ID: stable, and preferred over a text hash
-- wherever the game gives us one (spec §7).
SVSE.quests = SVSE.quests or {}
local q = SVSE.quests

q[784] = {
  title = "Besegra förrädarna",
  objectives = "Döda 10 sjömän från Kul Tiras, 8 marinsoldater från Kul Tiras och Lieutenant Benedict. Gå sedan tillbaka till Gar'Thok i Razor Hill.",
  description = "Människorna från Kul Tiras leddes av Admiral Proudmoore. De trängde in i Durotar och bröt det avtal som krigshövdingen slöt med Jaina Proudmoore för att besegra Archimonde för många år sedan.$b$bVi slog tillbaka anfallet och Tiragarde Keep föll. Men nu har amiralens soldater kommit tillbaka, ledda av Lieutenant Benedict. De har tagit fästningen igen och hotar vårt hemland på nytt. Dessa människor bryr sig inte om fred.$b$bVisa din ära. Res söderut till Tiragarde Keep och gör slut på inkräktarna.",
  progress = "Du har dina order, $N. Durotar är i fara. Gör klart din uppgift, annars får du gå med skammen.$B$BVisa din ära och besegra människorna i Tiragarde Keep.",
  completion = "Ryktet om ditt mod sprider sig fort, $C. Berättelsen om din seger vid Tiragarde Keep kommer att sjungas i Orgrimmar.",
}
q[786] = {
  title = "Stoppa Kolkars anfall",
  objectives = "Lar Prowltusk utanför Sen'jin Village vill att du förstör de 3 anfallsplanerna inne i Kolkar Crag.",
  description = "Sänk rösten, $c. Kolkar-centaurerna finns precis bakom bergsryggen i väster, i Kolkar Crag.$b$bI natt när de var ute och plundrade smög jag in i deras by. Där fick jag veta att de smutsiga djuren planerar tre anfall mot trollen och orcherna i Durotar.$b$bVi får inte låta dem lyckas. Kanske är du stark nog att smyga in i Kolkar Crag och förstöra deras planer.$b$bSenast jag såg dem hade de delat upp planerna mellan tre av sina ledare.",
  progress = "Centaurerna är ett ständigt problem för Horden. Vi kan inte låta dem anfalla vårt hemland.",
  completion = "Horden skulle så klart vinna om Kolkar-centaurerna anföll. Men genom att stoppa anfallet har vi sparat våra krigare från onödig blodspillan.$B$BOch lika säkert som att det finns sand i Tanaris kommer mer blod att spillas innan dessa svåra tider är över.$B$BDu har tjänat ditt folk väl, $C.",
}
q[787] = {
  title = "Den nya Horden",
  objectives = "Gå till Gornek i the Den.",
  description = "Throm'ka, $c. Jag är Eitrigg. Thrall har gett mig ansvaret för att träna nya rekryter.$b$bHorden är inte vad den en gång var. En gång lämnade jag Horden. Jag tyckte att alltför många lydde the Burning Legion och deras makthunger. När jag var borta togs jag till fånga av människor, men krigshövdingen räddade mig. Han berättade om en Horde utan demoner, ledd av shamanerna. Då kom jag tillbaka.$b$bGornek har fler instruktioner till dig.",
  completion = "Ännu en av Eitriggs rekryter, va?$B$BDet ser dystert ut för oss om det här är det bästa Horden kan få fram. Men strunt i det. När vi tycker att du är klar att lämna the Valley kommer du att vara en stolt krigare i Horden.",
}
q[788] = {
  title = "Första striden",
  objectives = "Döda 10 fläckiga vildsvin och gå sedan tillbaka till Gornek i the Den.",
  description = "Först måste vi göra dig starkare. Jag skulle kunna skicka dig till the Barrens för att jaga kodo, men ärligt talat är du mer värd för oss levande än död.$b$bJag tror att du passar bättre mot de fläckiga vildsvinen som finns norr om här.",
  progress = "Du kommer väl inte tillbaka för att påstå att du är klar, $N? Nej, självklart inte. Jag tror bättre om dig än så.",
  completion = "Hmmm, inte illa, $N. Men bli inte högfärdig – du kommer att möta mycket tuffare fiender än vildsvin.$b$bDu har ändå visat vad du går för. Nästa gång blir motståndaren mycket farligare, så du behöver bättre skydd.",
}
q[789] = {
  title = "Skorpionens gadd",
  objectives = "Hämta 10 skorpionsvansar till Gornek i the Den.",
  description = "Både starka krigare och klumpiga nybörjare har dött av en skorpions giftiga gadd. Du hittar många skorpioner nordväst om här. Ta med tio av deras svansar som bevis på att du klarar strid.$b$bMotgiftet mot gadden görs faktiskt av giftet från gadden själv. Vi har alltid mycket motgift redo för att bota unga vildhjärnor som du...$b$bMen du behöver nog inget sådant, eller hur?",
  progress = "Skalet på en skorpion är inte så tjockt att en modig $C behöver ge upp. Slå hårt och tveka inte – då blir de lätta byten.",
  completion = "Det finns en viktig läxa att lära av att slåss mot skorpioner. Både den minsta och den största fienden kan bli din död. I en hård strid kan vad som helst gå fel.$b$bJag har inget mer att lära dig, $N. Du har gjort det bra, och jag ska följa dig med stort intresse.",
}
q[790] = {
  title = "Sarkoth",
  objectives = "Döda Sarkoth och ta med hans klo tillbaka till Hana'zua.",
  description = "$C! Jag trodde att jag skulle dö här utan att någon fick veta det. När jag jagade skorpioner i the Valley stötte jag på en riktigt elak sådan. Jag kastade mig över den och lyckades skada dess klo, men sedan slöt den sig om mitt ben.$b$bJag var inte redo för gadden. Den högg ner i mitt bröst och skar upp mig så att blodet rann. Snälla, du måste döda skorpionen för mig! Min ära måste räddas! Jag slogs mot den på klippan i söder.",
  progress = "Ahhh... min far sa alltid att jag aldrig skulle bli något. Och här ligger jag under ett träd medan livet rinner ur mig. Jag är rädd att han hade rätt.$b$bJag vill åtminstone dö med vetskapen att min sista fiende också ligger död.",
  completion = "Mitt slag räckte inte för att döda honom, men när jag ser skadan jag gjorde känner jag en liten stolthet. Den lilla stoltheten är allt jag har om jag dör, och då fyller den korta listan över mitt livs bedrifter mig med vrede.",
}
q[791] = {
  title = "Gör din del",
  objectives = "Furl Scornbrow i vakttornet i Razor Hill vill ha 8 tygbitar.",
  description = "Åldern har gjort mig oduglig i strid. Nu gör jag mig nyttig på andra sätt.$b$bHärifrån håller jag utkik efter fiender. Ju starkare vi blir här, desto mer sällan behöver jag blåsa i signalhornet.$b$bFör att få tiden att gå tillverkar jag saker som hjälper yngre och starkare krigare att försvara vårt hemland.$b$bTill dig kan jag göra en väska för dina saker. Om du vill ha en sådan, ta med lite tyg till mig. Det är ett material som människor och centaurer ofta har.",
  progress = "Jag slogs stolt vid krigshövdingens sida när dessa marker togs. Striderna har lämnat spår på min hud.$b$bHordens ära försvarades av min yxa och mitt stridsrop när Archimonde besegrades, då vi tvingades sluta ett oheligt förbund med människor och alver.$b$bMen att vara vakt och hantverkare har gett mig ett nytt värde.",
  completion = "Utmärkt, $N. Varje bra $C hittar säkert nytta för den här väskan på slagfältet.$b$bJag hälsar din kraft och din vilja att dö för Horden!",
}
q[792] = {
  title = "Elaka demoner",
  objectives = "Döda 12 elaka demoner.$B$BGå tillbaka till Zureetha Fargaze utanför the Den.",
  description = "Jag tror att the Valley of Trials kommer att lära dig mycket, unga $c.$B$BJag skickades till the Valley för att vägleda dig, men jag har hittat något ont som växer här...$B$BEn grupp som kallar sig the Burning Blade har ett gömställe här i the Valley of Trials. De håller till i en grotta i nordost, och deras elaka demoner har strömmat ut därifrån och ställer till kaos.$B$BDin första uppgift mot the Burning Blade är att besegra dessa demoner. Döda många, och kom tillbaka till mig om du överlever.",
  progress = "För att bevisa dig mot the Burning Blade måste du först besegra deras elaka demoner. Kom tillbaka till mig när du har gjort det.",
  completion = "Du har gjort det bra, $N.$b$bDe elaka demonerna var bara husdjur till de mörkare krafterna i the Burning Blade, men din seger över dem visar att större dåd väntar.",
}
q[794] = {
  title = "Burning Blade-medaljongen",
  objectives = "Ta Burning Blade-medaljongen till Zureetha Fargaze utanför the Den.",
  description = "Genom mina syner ser jag att ett mäktigt föremål ligger djupt inne i Burning Blade-sekten, vaktat av vidunder och svart magi.$B$BDet kallas Burning Blade-medaljongen. Din nästa uppgift är att hitta det och ta det ut därifrån.$B$BMen var försiktig. Medaljongen kan bäras av en tjänare till the Burning Blade, och då är han starkare än de demoner du redan har mött.$B$BGå, $N. Du hittar deras gömställe i en grotta i nordväst.",
  progress = "Är din uppgift klar, $N? Har du Burning Blade-medaljongen?",
  completion = "Du hittade den! Bra gjort!$b$bDitt arbete i Burning Blade-sekten är viktigt för att rensa bort kulten från the Valley of Trials. Men jag är rädd att de har större planer i vårt land.$b$bVi har inte sett det sista av dem.",
}
q[804] = {
  title = "Sarkoth",
  objectives = "Berätta för Gornek i the Den om hur det är med Hana'zua.",
  description = "Att se vad du har gjort för mig ger mig nytt mod. Jag får inte falla så lätt! Jag måste hålla ut!$b$bMen jag kan ändå inte gå tillbaka till the Den på egen hand. Snälla, $n, gå till the Den och berätta för Gornek hur det är med mig. Han kan nog hjälpa mig.",
  completion = "Så som du beskriver vidundret måste det vara Sarkoth! Inte undra på att Hana'zua blev överfallen. Hjälp skickas till honom med en gång, oroa dig inte mer för honom.$b$bMen jag måste säga att jag är mycket imponerad av att du dödade Sarkoth. Det är en bedrift att vara stolt över, $N. Och att du slogs för en främlings ära mitt bland dina andra uppgifter gör din egen ära ännu större.",
}
q[805] = {
  title = "Rapportera till Sen'jin Village",
  objectives = "Prata med Master Gadrin i Sen'jin Village.",
  description = "Dina prövningar mot the Burning Blade är över... här i the Valley. Men jag vill att du berättar vad du har sett.$B$BGå till trollbyn Sen'jin och sök upp Master Gadrin. Sen'jin Village ligger öster om the Valley, och sedan till höger vid vägskälet.$B$BBerätta för Gadrin om the Burning Blade, och att de har nått the Valley of Trials. Ta reda på om de också har nått Sen'jin.$B$BGå, $N, och skynda dig. Jag är rädd att ondskan i Burning Blade-sekten bara är början på något mycket större...",
  completion = "Hm... din rapport kommer olyckligt. The Burning Blade syns inte här i Sen'jin, men deras ondska har slagit rot utanför kusten, på the Echo Isles.$b$bOrcherna är vänner med Darkspear-trollen. Ärliga vänner. Vi vill hjälpa orcherna, men... vi behöver också hjälp.$b",
}
q[806] = {
  title = "Mörka stormar",
  objectives = "Ta Fizzles klo till Orgnil Soulscar i Razor Hill.",
  description = "Vi kan inte låta the Burning Blade få fäste i Durotar! Vi måste krossa dem innan deras ondska sprider sig!$B$BJag har gjort egna efterforskningar. En svartkonstnär från the Burning Blade, goblinen Fizzle Darkstorm, har slagit läger i Thunder Ridge i nordväst. Där sprider han och hans anhängare kaos.$B$BHitta Fizzle, besegra honom och ta med hans döda klo till mig!",
  progress = "Hittade du Fizzle, $N? Han och resten av the Burning Blade måste rensas bort från våra marker!",
  completion = "Aha! Du fick honom!$b$bDu gör din klan stolt, $N. Och tack vare dig är Durotar fritt från ännu en ond tjänare.",
}
q[808] = {
  title = "Minshinas skalle",
  objectives = "Hämta Minshinas skalle från kraftcirkeln på the Echo Isles.$B$BTa den till Master Gadrin i Sen'jin Village.",
  description = "Jag hör min bror Minshinas röst kalla på mig i mina drömmar.$B$BHan togs av Zalazane, svartkonstnären på the Echo Isles i öster. Och han är död.$B$BMen döden är ingen frihet för min bror. Minshinas ande fångades i hans egen skalle av Zalazanes magi. I mina drömmar ser jag den bland andra skallar, i en kraftcirkel på den största av the Echo Isles. Så länge den ligger där är min brors själ förlorad.$B$BSnälla, $N. Hitta cirkeln och hämta Minshinas skalle. Ta den till mig.$B$BBefria honom!",
  progress = "Har du min brors skalle, $N? Är han äntligen fri?",
  completion = "Tack, $N. Du har räddat Minshina. Du har räddat min brors ande från slaveri!",
}
q[809] = {
  title = "Ak'Zeloth",
  objectives = "Prata med Ak'Zeloth i the Barrens.",
  description = "Sedan det stora kriget då the Burning Legion besegrades har jag letat efter spår av demonisk ondska bland orcherna. Halsbandet du gav mig bekräftar det jag var rädd för.$B$BDet tillhör the Burning Blade, en kult som samlas kring ett föremål med demonisk kraft. Det kallas Demonfröet och finns i the Barrens, på toppen av Dreadmist Peak. Det måste förstöras!$B$BGå till Far Watch Post vid gränsen till the Barrens i väster och prata med min medhjälpare Ak'Zeloth. Han berättar mer.",
  completion = "Vill Neeru att Demonfröet förstörs? Märkligt...$b$bNåväl. Om han vill att fröet försvinner ska jag berätta hur man tar bort det.",
}
q[812] = {
  title = "Jakten på motgiftet",
  objectives = "Hitta Kor'ghan i Orgrimmar och hämta giftsvansmotgiftet. Ta sedan motgiftet till Rhinag nära Durotars nordvästra gräns.",
  description = "$N... du kommer precis i rätt tid. Jag hoppas bara att du är lika snabb som du är punktlig.$B$BJag var oförsiktig när jag slogs mot några giftsvansar här i närheten, och en av dem stack mig djupt. Jag känner hur giftet gör mig svagare medan vi pratar. I den här farten har jag ungefär en timme kvar att leva. Men jag behöver din hjälp för att klara mig...$B$BKor'ghan i Orgrimmar vet hur man gör motgiftet. Hitta honom... och skynda dig, $N. Jag håller inte ut så mycket längre. Han borde vara i the Cleft of Shadow.",
  progress = "Jag är nästan glad att jag inte kan gå tillbaka till Sen'jin som jag är nu. Min svaghet och dumhet skulle säkert bli utskrattad.",
  completion = "$N, du har räddat mitt liv. Tack.$B$BTa det här; jag hoppas att det kan hjälpa dig på dina resor, eller ge dig några mynt. Som du säger kommer jag inte att använda det på ett bra tag. Kor'ghan kommer att låta mig göra fler av sina ritualer tills jag bevisat mig. Fler vildsvin att döda, fler skorpionsvansar att samla... <suck>",
}
q[4641] = {
  title = "Din plats i världen",
  objectives = "Prata med Gornek. Kaltunk märkte ut honom på din karta. Gornek bor i the Den, ett hus i väster.",
  description = "Äntligen är du gammal nog, $N... gammal nog att slåss för Horden. Att vinna ära för krigshövdingen.$B$BJa...$B$B<Kaltunk tittar noga på dig.>$B$BDu kommer att duga bra.$B$BDu vill säkert hitta en stor drake eller demon och strypa den med bara händerna. Men det är nog klokare att börja med något lite mindre... farligt.$B$B<Kaltunk skrattar.>$B$BGå till Gornek. Han har en uppgift som passar en ung $c bättre. Du hittar Gornek i the Den, i väster.",
  progress = "Skalet på en skorpion är inte så tjockt att en modig $C behöver ge upp. Slå hårt och tveka inte – då blir de lätta byten.",
  completion = "Ännu en av Kaltunks rekryter, va?$B$BDet ser dystert ut för oss om det här är det bästa Horden kan få fram. Men strunt i det. När vi tycker att du är klar att lämna the Valley kommer du att vara en stolt $C i Horden.",
}
