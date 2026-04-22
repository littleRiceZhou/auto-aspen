% =========================================================================
% 透平膨胀机一维计算主程序
% 功能：给定进口参数，计算叶轮直径和转速
% 输入：p0-进口压力(Pa), T0-进口温度(K), p3-出口压力(Pa), 
%       mv-体积流量(Nm/s), ns-比转速(目前直接填0.575)
% 输出：D1-叶轮直径(m), nnnr-转速(rpm)，
% =========================================================================

function [eta] = turbExpander_1D(p0, T0, p3, mv,fluid, ns)
    % 默认比转速
    if nargin < 6
        ns = 0.575;
    end
    
    % 物性参数设置（根据工质选择）
    % 这里以甲烷为例，其他工质见附注

    

    
    % 通用气体常数
    R = 8.314;  % J/(mol·K)
    
    % ==================== 1. 工质物性读取 ====================
    switch fluid
        case 'H2'
            fl9 = importdata('H2.csv').data;
            Rm = 4124.00794;      % 气体常数 J/(kg·K)
            M = 2.016e-3;         % 摩尔质量 kg/mol
            RMCPT = 1;
        case 'CH4'
            fl9 = importdata('CH4.csv').data;
            Rm = 518.23225;
            M = 16.04e-3;
            RMCPT = 2;
        case 'C2H6'
            fl9 = importdata('C2H6.csv').data;
            Rm = 276.4881942;
            M = 30.07e-3;
            RMCPT = 3;
        case 'N2'
            fl9 = importdata('N2.csv').data;
            Rm = 296.716631;
            M = 28.01e-3;
            RMCPT = 4;
        case 'C3H8'
            fl9 = importdata('C3H8.csv').data;
            Rm = 189;
            M = 44e-3;
            RMCPT = 5;
        case 'iC4H10'
            fl9 = importdata('iC4H10.csv').data;
            Rm = 143.3;
            M = 58e-3;
            RMCPT = 6;
         case 'nC4H10'
            fl9 = importdata('nC4H10.csv').data;
            Rm = 143.3;
            M = 58e-3;
            RMCPT = 7;
        case 'C2H4'
            fl9 = importdata('C2H4.csv').data;
            Rm = 296.9;
            M = 28e-3;
            RMCPT = 8;
        case 'CO2'
            fl9 = importdata('CO2.csv').data;
            Rm = 189;
            M = 44e-3;
            RMCPT = 9;
        case 'CO'
            fl9 = importdata('CO.csv').data;
            Rm = 296.9;
            M = 28e-3;
            RMCPT = 10;
        case 'H2O'
            fl9 = importdata('H2O.csv').data;
            Rm = 461.9;
            M = 18e-3;
            RMCPT = 11;
        case 'O2'
            fl9 = importdata('O2.csv').data;
            Rm = 259.8;
            M = 32;
            RMCPT = 12;
        case 'R125'
            fl9 = importdata('C2HF5.csv').data;
            Rm = 69.3;
            M = 120e-3;
            RMCPT = 13;
    end
    
    % 物性数据列说明:
    % col2-温度(K), col3-压力(Pa), col4-密度(kg/m3), col5-焓(J/kg), col6-熵(J/kg·K)
    % col7-定压比热(J/kg·K), col8-定容比热(J/kg·K), col9-声速(m/s)
    % col11-动力粘度(Pa·s), col12-导热系数(W/m·K)

    RMCP = importdata('NMC9.csv');

    m = mv*RMCP(RMCPT,1)/3600;
    % ==================== 2. 进口状态计算 ====================
    % 压力插值查找进口状态
            fl91 = sortrows(fl9,3);
            p0x = max(find(fl91(:,3)<p0));
            p0s = min(find(fl91(:,3)>p0));
            mpgo = ismember(p0,fl91(:,3));
             lll = fl9(:,2);
            if mpgo == 0
                for i = 1:length(lll)
                    if fl91(i,3) < p0
                        if fl91(i,3) ~= fl91(p0x,3)
                            j = i;
                        elseif fl91(i,3) == fl91(p0x,3)
                            kfl(i-j,:) = fl91(i,:);
                        end
                    elseif fl91(i,3) > p0
                        if fl91(i,3) == fl91(p0s,3)
                            kfl(i-j,:) = fl91(i,:);
                        end
                    end
                end
                j = 0;
            else
                for i = 1:length(lll)
                    if fl91(i,3)<p0
                        j = i;
                    elseif fl91(i,3)==p0
                        kfl(i-j,:) = fl91(i,:);
                    end
                end
                j = 0;
            end
             %%%%%%%求解输入的入口温度的位置，给后续的插值做准备
            fl92 = sortrows(kfl,2);
            T0x = max(find(fl92(:,2)<T0));
            T0s = min(find(fl92(:,2)>T0));
            mTgo = ismember(T0,fl92(:,2));
            ll = fl92(:,2);
            if mTgo == 0
                for i = 1:length(ll)
                    if fl92(i,2)<T0
                        if fl92(i,2) ~= fl92(T0x,2)
                            j = i;
                        elseif fl92(i,2) ==fl92(T0x,2)
                            kf(i-j,:) = fl92(i,:);
                        end
                    elseif fl92(i,2) > T0
                        if fl92(i,2) == fl92(T0s,2)
                            kf(i-j,:) = fl92(i,:);
                        end
                    end
                end
                j = 0;
            else
                for i = 1:length(ll)
                    if fl92(i,2)<T0
                        j = i;
                    elseif fl92(i,2)==T0
                        kf(i-j,:) = fl92(i,:);
                    end
                end
                j = 0;
            end
            %%%%%%%%插值，这里采用线性插值，后期看是否有使用最小二乘法的必要
            %%%%%%第2列是温度，第3列是压力，第4列是密度，第5列是焓，第6列是熵；
            %%%%%%第7列是定压比热，第8列是定容比热，第9列是声速，第11列是动力粘度，第12列是导热系数；
            pp0 = kf(:,3);
            TT0 = kf(:,2);
            rrho0 = kf(:,4);
            hh0 = kf(:,5);
            ss0 = kf(:,6);
            ccp0 = kf(:,7);
            ccv0 = kf(:,8);
            ccs0 = kf(:,9);
            rhoF = scatteredInterpolant(pp0,TT0,rrho0,'linear');
            rho0 = rhoF(p0,T0);
            hF = scatteredInterpolant(pp0,TT0,hh0,'linear');
            h0 = hF(p0,T0);
            sF = scatteredInterpolant(pp0,TT0,ss0,'linear');
            s0 = sF(p0,T0);
            cpF = scatteredInterpolant(pp0,TT0,ccp0,'linear');
            cp0 = cpF(p0,T0);
            cvF = scatteredInterpolant(pp0,TT0,ccv0,'linear');
            cv0 = cvF(p0,T0);
            csF = scatteredInterpolant(pp0,TT0,ccs0,'linear');
            cs0 = csF(p0,T0);
            

    
    % ==================== 3. 等熵膨胀计算出口状态 ====================
                %%%%%%入口所有物理量全部导出，接下来寻找等熵过程下的出口温度
            %%%%%%%求解输入的入口压力的位置，给后续的插值做准备
            fl91 = sortrows(fl9,3);
            p3x = max(find(fl91(:,3)<p3));
            p3s = min(find(fl91(:,3)>p3));
            mpgo = ismember(p3,fl91(:,3));
            if mpgo == 0
                for i = 1:length(lll)
                    if fl91(i,3) < p3
                        if fl91(i,3) ~= fl91(p3x,3)
                            j = i;
                        elseif fl91(i,3) == fl91(p3x,3)
                            kfo(i-j,:) = fl91(i,:);
                        end
                    elseif fl91(i,3) > p3
                        if fl91(i,3) == fl91(p3s,3)
                            kfo(i-j,:) = fl91(i,:);
                        end
                    end
                end
                j = 0;
            else
                for i = 1:length(lll)
                    if fl91(i,3)<p3
                        j = i;
                    elseif fl91(i,3)==p3
                        kfo(i-j,:) = fl91(i,:);
                    end
                end
                j = 0;
            end
            %%%%$$$找等熵过程位置
            fl93 = sortrows(kfo,6);
            se3x = max(find(fl93(:,6)<s0));
            se3s = min(find(fl93(:,6)>s0));
            msgo = ismember(s0,fl93(:,6));
            lls = fl93(:,6);
            if msgo == 0
                for i = 1:length(lls)
                    if fl93(i,6)<s0
                        if fl93(i,6) ~= fl93(se3x,6)
                            j = i;
                        elseif fl93(i,6) == fl93(se3x,6)
                            kn(i-j,:) = fl93(i-1,:);
                            kn(i-j+1,:) = fl93(i,:);
                        end
                    elseif fl93(i,6)>s0
                        if fl93(i,6) == fl93(se3s,6)
                            kn(i-j+1,:) = fl93(i,:);
                            kn(i-j+2,:) = fl93(i+1,:);
                        end
                    end
                end
                j = 0;
            else
                for i = 1:length(lls)
                    if fl93(i,6)<s0
                        j = i;
                    elseif fl93(i,6) == s0
                        kn(i-j,:) = fl93(i,:);
                    end
                end
                j = 0;
            end
            %%%%%%等熵过程下出口数值插值（只插温度和焓即可，其他值用不着）
            % %%%%%这里依旧采用线性插值，后期看是否有使用最小二乘法的必要。
            ppe3 = kn(:,3);
            sse3 = kn(:,6);
            TTe3 = kn(:,2);
            rrhoe3 = kn(:,4);
            hhe3 = kn(:,5);
            rhoeF3 = scatteredInterpolant(ppe3,sse3,rrhoe3,'linear');
            rhoe3 = rhoeF3(p3,s0);
            heF3 = scatteredInterpolant(ppe3,sse3,hhe3,'linear');
            he3 = heF3(p3,s0);
            TeF3 = scatteredInterpolant(ppe3,sse3,TTe3,'linear');
            Te3 = TeF3(p3,s0);

            %%%%%%开始计算，计算理想焓降等量
            dhs = h0 - he3; %理想焓降
            dhsrott = dhs*0.49; %叶轮内理想焓降
            P = m*dhs*0.85;
            dhsstaa = dhs - dhsrott; %导叶内理想焓降
            cs = (2*dhs)^(1/2);
            c1 = 0.95*(2*dhsstaa)^(1/2);%导叶出口实际速度
            %%%%%%%%%%%第一个判据约束：设c1气流角75°，叶轮-10°进气，根据铝合金和钛合金容许最大线速度做第一次预判断，若超速，做调整。
            cest = c1*(sind(85)/sind(80));
            %%%%%%%%喷嘴出口实际焓值
            h1 = h0 - 0.95^2*dhsstaa;
            h1s = h0 - dhsstaa;


       fl9n = sortrows(fl9,5);
       k91b  = zeros(length(lll),1);
for k = 1:length(lll)
    k91b(k,1) = abs(fl9n(k,5)-h1s);
end
    [DDD, II9] = mink(k91b,1000);
    fl91nb = fl9n(II9,:);
for i1 = 1:1000
    k91nb(i1,1) = abs(fl91nb(i1,6)-s0);
end
    [SSS, II8] = mink(k91nb,6);
    fl91nc = fl91nb(II8,:);


%%%计算出等熵过程下喷嘴出口数值%%%%

p1 = fl91nc(3,3);

T1 = fl91nc(3,2);
rho1 = fl91nc(3,4);
cccc1 = fl91nc(3,9);

            %%%算一下0,1,3位置的压缩因子Z(3在后面再计算，现在参数没导出完全）
            Ze1 = rho1*Rm*T1/(p1);
            Ze0 = rho0*Rm*T0/(p0);
            kapa0 = cp0/cv0;
            n0 = kapa0/(kapa0-0.95^2*(kapa0-1));
            cmi = (2*Ze0*Rm*T0*(kapa0/(kapa0-1))*(n0-1)/(n0+1))^(1/2);
            Mayg = c1/cccc1;
            %%%%%%算一下喷嘴能量损失%%%%%%%
            qn = (1-0.95^2)*dhsstaa;
            %%%%%%轮径比预设0.45
            u3m = 0.45*cest;
            omega2 = c1*(sind(15)/sind(80));
            D1 = (m/(3.14159*0.05*omega2*sind(80)*rho1*0.965))^(1/2);
            nnnr = cest*60/(D1/2)/2/3.14159;

       % ==================== 分级判断 ================
       kcl = 0;                 
       if D1 <= 0.6
                if kcl == '0'
                    if cest <= 350
                        if nnnr <= 50000
                            if Mayg < 0.9999999
                                F_Message = '该输入参数不用分级，请直接设计，喷嘴亚音速';
                                pja1 = 1;
                            elseif Mayg < 1.225
                                F_Message  = '该输入参数不用分级，请直接设计，喷嘴跨音速';
                                pja1 = 2;
                            elseif Mayg >=1.225
                                F_Message  = '喷嘴马赫数过大，请运行分级迭代程序';
                                pja1 = 4;
                            end
                        else
                            F_Message  = '叶轮转速过大，请运行分级迭代程序';
                            pja1 = 5;
                        end
                    elseif cest <=500
                        if nnnr <= 50000
                            if Mayg < 0.9999999
                                F_Message  = '该输入参数可使用钛合金叶轮可不分级，喷嘴亚音速，若坚持铝合金叶轮，运行分级迭代程序';
                                pja1 = 31;
                            elseif Mayg < 1.225
                                F_Message  = '该输入参数可使用钛合金叶轮可不分级，喷嘴跨音速，若坚持铝合金叶轮，运行分级迭代程序';
                                pja1 = 32;
                            elseif Mayg >=1.225
                                F_Message  = '喷嘴马赫数过大，请运行分级迭代程序';
                                pja1 = 4;
                            end
                        else
                            F_Message  = '叶轮转速过大，请运行分级迭代程序';
                            pja1 = 5;
                        end
                    else
                        F_Message = '叶轮外缘线速度过大，请运行分级迭代程序';
                        pja1 = 6;
                    end
                elseif kcl== '1'
                    if cest <=500
                        if nnnr <= 50000
                            if Mayg < 0.9999999
                                F_Message  = '该输入参数不用分级，请直接设计，喷嘴亚音速';
                                pja1 = 1;
                            elseif Mayg < 1.225
                                F_Message  = '该输入参数不用分级，请直接设计，喷嘴跨音速';
                                pja1 = 2;
                            elseif Mayg >=1.225
                                F_Message  = '喷嘴马赫数过大，请运行分级迭代程序';
                                pja1 = 4;
                            end
                        else
                            F_Message  = '叶轮转速过大，请运行分级迭代程序';
                            pja1 = 5;
                        end
                    else
                        F_Message  = '叶轮外缘线速度过大，请运行分级迭代程序';
                        pja1 = 6;
                    end
                end
            elseif D1 > 0.6
                F_Message  = '叶轮直径过大，请运行分级迭代程序';
                pja1 = 7;
            end
            
       % ==================== 实际效率计算 ================
      dhu = P/m;
      uuu = nnnr*2*3.14/60*D1/2;
       psii = dhu/(uuu^2/1);
       cm3 = c1*(0.4-rand(1)*0.05);
       phi = cm3/uuu;
       xxx = phi-0.24;
       yyy = psii - 0.94;
       yts = xxx^2/0.045^2+yyy^2/0.04^2;
       eta = 0.9 - 0.025*yts^(1/2);



% =========================================================================
% 附注：工质气体常数 Rm 对照表
% -------------------------------------------------------------------------
% 工质     | Rm (J/kg·K) | M (kg/mol)
% -------------------------------------------------------------------------
% H2       | 4124.00794   | 2.016e-3
% CH4      | 518.23225    | 16.04e-3
% C2H6     | 276.4881942  | 30.07e-3
% N2       | 296.716631   | 28.01e-3
% -------------------------------------------------------------------------
% 
% 物性数据文件格式说明 (.csv):
% 列号  | 内容
% -----|------------------
% 2     | 温度 T (K)
% 3     | 压力 P (Pa)
% 4     | 密度 ρ (kg/m³)
% 5     | 焓 h (J/kg)
% 6     | 熵 s (J/kg·K)
% 7     | 定压比热 cp (J/kg·K)
% 8     | 定容比热 cv (J/kg·K)
% 9     | 声速 a (m/s)
% 11    | 动力粘度 μ (Pa·s)
% 12    | 导热系数 λ (W/m·K)
% =========================================================================
